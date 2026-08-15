from sqlalchemy import (
    ARRAY,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred
from sqlalchemy.sql import func

from app.db.database import Base


class Interview(Base):
    """One mock interview: the problem, the transcript, and what it revealed.

    The transcript is JSONB on the row rather than a table of turns. A
    conversation is only ever read whole, never queried across, and appending
    to a list is cheaper to reason about than ordering rows by a sequence that
    has to stay gapless.
    """

    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # What the interview is about, captured at the time: the catalogue can
    # change, and a finished interview should keep describing what it was.
    topic = Column(String(80))
    platform = Column(String(20))
    problem_name = Column(String(255))
    problem_url = Column(String(500))
    # "open" or "finished". A closed interview accepts no more turns.
    status = Column(String(20), nullable=False, server_default="open")
    transcript = Column(JSONB, nullable=False, server_default="[]")
    # The agent's closing assessment. Kept apart from the weak-topic scores on
    # purpose — see the notes: demonstrated weakness is real signal, but it is
    # a different kind of evidence from a pass rate and mixing them would make
    # the score unexplainable.
    findings = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime)


class Revision(Base):
    """The revision schedule for one solved problem.

    Kept as a row rather than recomputed, because the schedule depends on what
    happened at each earlier revisit, not only on the original solve date.
    """

    __tablename__ = "revisions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "external_problem_id", name="uq_revision_problem"
        ),
        Index("ix_revisions_due", "user_id", "due_on"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(20), nullable=False)
    external_problem_id = Column(String(100), nullable=False)
    problem_name = Column(String(255))
    first_solved_at = Column(DateTime, nullable=False)
    # Index into revision_schedule.INTERVALS.
    step = Column(Integer, nullable=False, server_default="0")
    # Null means retired: recalled through the whole ladder, or already older
    # than it when this feature first saw the problem.
    due_on = Column(Date)
    last_reminded_on = Column(Date)


class SyncState(Base):
    """Whether a platform's history has ever been imported in full.

    Incremental sync resumes from the newest stored submission, which is only
    correct if an earlier import actually finished. Without this row a single
    stray submission — from an import that was interrupted — makes the app
    believe it is up to date and the rest of the history is never fetched.
    """

    __tablename__ = "sync_states"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_sync_user_platform"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(20), nullable=False)
    # Set only after a full fetch has been committed. Null means "never
    # finished", which is what forces the next sync to start from scratch.
    full_import_completed_at = Column(DateTime)
    last_synced_at = Column(DateTime)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    codeforces_handle = Column(String(50))
    # "owner/repo" of a LeetHub-synced GitHub repository.
    leetcode_repo = Column(String(140))
    # Public LeetCode username, for profile totals the repo cannot supply.
    leetcode_username = Column(String(100))
    # The avatar is kept in the database rather than on disk: free hosting
    # gives every deploy a fresh filesystem, so an uploaded file would vanish
    # on the next release. Resized to 256px on upload, it costs ~40KB a row.
    #
    # Deferred because every request that loads a user would otherwise drag the
    # image bytes along with it; only the avatar endpoint selects the column.
    avatar = deferred(Column(LargeBinary))
    # Doubles as the "has a photo" flag, so `has_avatar` needs no extra query.
    avatar_mime = Column(String(30))
    # Bumped whenever every existing session should stop working — currently
    # only a password change. Tokens carry the value they were minted with, so
    # a mismatch is what lets a stateless JWT be revoked without a session
    # store.
    token_version = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime, server_default=func.now())

    @property
    def has_avatar(self) -> bool:
        return self.avatar_mime is not None


class EmailChangeRequest(Base):
    """A pending move to a new address, proved by a code sent to that address.

    Kept as a row rather than held in memory so a restart does not strand a
    user mid-change, and so the attempt counter survives too: without it, the
    six-digit code could be guessed by retrying.
    """

    __tablename__ = "email_change_requests"
    __table_args__ = (
        # Every verify looks up the newest live request for one user.
        Index("ix_email_change_requests_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    new_email = Column(String(255), nullable=False)
    # Hashed with the same bcrypt context as passwords: a database leak should
    # not hand over a live code, and five attempts makes the cost irrelevant.
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, server_default="0")
    # Set once the change goes through, so a code cannot be replayed.
    consumed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "external_problem_id", "solved_at"),
        # Every dashboard query filters on this pair before aggregating.
        Index("ix_submissions_user_id_verdict", "user_id", "verdict"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform = Column(String(20), nullable=False)
    external_problem_id = Column(String(100), nullable=False)
    problem_name = Column(String(255))
    tags = Column(ARRAY(String), nullable=False, server_default="{}")
    # Codeforces rates numerically (800-3500); LeetCode only says
    # Easy/Medium/Hard, so each platform fills one column and leaves the other
    # null rather than one being coerced into the other's scale.
    difficulty_rating = Column(Integer)
    difficulty_label = Column(String(10))
    verdict = Column(String(40))
    solved_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class DailyPlan(Base):
    """One generated practice plan per user per day.

    Stored rather than generated on demand so revisiting the dashboard costs no
    model call, and so the plan does not change between page loads.
    """

    __tablename__ = "daily_plans"
    __table_args__ = (UniqueConstraint("user_id", "plan_date"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_date = Column(Date, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class WeeklyReport(Base):
    """A frozen snapshot of one finished week.

    Scoring rules will change; a report of what happened in March should keep
    saying what it said in March rather than being rewritten by today's formula.
    """

    __tablename__ = "weekly_reports"
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Reminder(Base):
    """One generated revision reminder.

    Rows are the hand-off point between generation and delivery: the dashboard
    reads them today, and an email sender can read the same rows later without
    the engine changing.
    """

    __tablename__ = "reminders"
    __table_args__ = (
        UniqueConstraint("user_id", "run_date", "kind", "platform", "subject"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    run_date = Column(Date, nullable=False)
    kind = Column(String(20), nullable=False)
    # Which platform the reminder is about, so a filtered dashboard can show
    # only its own reminders.
    platform = Column(String(20), nullable=False)
    # Stable identity for dedupe: a tag name, or "platform:problem_id".
    subject = Column(String(200), nullable=False)
    title = Column(String(255), nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class LeetCodeProfile(Base):
    """Latest public-profile snapshot for a user.

    LeetHub only sees problems solved after it was installed; the profile knows
    the real totals. One row per user, overwritten on each sync.
    """

    __tablename__ = "leetcode_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    synced_at = Column(DateTime, server_default=func.now())
