from sqlalchemy import (
    ARRAY,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    codeforces_handle = Column(String(50))
    # "owner/repo" of a LeetHub-synced GitHub repository.
    leetcode_repo = Column(String(140))
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
