import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import (
    CodeforcesError,
    CodeforcesHandleError,
    fetch_user_submissions,
)
from app.clients.email_client import MailError, send_mail
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import (
    DailyPlan,
    EmailChangeRequest,
    Interview,
    LeetCodeProfile,
    Reminder,
    Revision,
    Submission,
    SyncState,
    User,
    WeeklyReport,
)
from app.schemas.user import (
    ChangePassword,
    DeleteAccount,
    PendingEmailChange,
    RequestEmailChange,
    SetCodeforcesHandle,
    SetLeetcodeRepo,
    SetLeetcodeUsername,
    Token,
    UpdateProfile,
    UserOut,
    VerifyEmailChange,
)
from app.services import email_change_service, profile_service
from app.services.email_change_service import EmailChangeError
from app.services.profile_service import ProfileError

log = logging.getLogger("solvix.users")

router = APIRouter(prefix="/users", tags=["users"])


def _now() -> datetime:
    """Naive UTC, matching the timezone-less DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


async def _check_handle_exists(handle: str) -> None:
    """Refuse a handle Codeforces does not know.

    A typo used to save happily and then surface days later as a failed
    morning sync, which reads as the app being broken rather than as a wrong
    handle. One request, asking for a single submission, turns that into an
    immediate answer.

    An outage is not a wrong handle, so only an explicit rejection blocks the
    save: refusing to let somebody rename themselves because Codeforces is
    down would be worse than the problem being solved.
    """
    try:
        await fetch_user_submissions(handle, count=1)
    except CodeforcesHandleError as exc:
        raise ProfileError(f"Codeforces does not know the handle '{handle}'") from exc
    except CodeforcesError:
        log.warning("could not verify handle %s; accepting it", handle)


@router.patch("/me", response_model=UserOut)
async def update_profile(
    payload: UpdateProfile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit the parts of an account the user owns.

    Email is not among them: it identifies the account and changing it would
    need a confirmation round-trip to the new address to be worth anything.
    """
    sent = payload.model_fields_set

    try:
        if "display_name" in sent:
            current_user.display_name = profile_service.clean_display_name(
                payload.display_name
            )
        if "codeforces_handle" in sent:
            handle = (payload.codeforces_handle or "").strip()
            # Clearing the handle would strand the dashboard, which treats a
            # missing handle as "this account has not been set up yet".
            if not handle:
                raise ProfileError("A Codeforces handle is required")
            if handle != current_user.codeforces_handle:
                await _check_handle_exists(handle)
            current_user.codeforces_handle = handle
        if "leetcode_username" in sent:
            username = (payload.leetcode_username or "").strip()
            current_user.leetcode_username = username or None
        if "leetcode_repo" in sent:
            current_user.leetcode_repo = profile_service.clean_repo(
                payload.leetcode_repo
            )
    except ProfileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/password", response_model=Token)
async def change_password(
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the password, proving ownership with the current one first.

    Changing a password is how someone locks an intruder out, so every token
    minted before this moment stops being accepted: `token_version` is bumped
    and the dependency compares it against the `tv` claim. That retires the
    caller's own token too, so a replacement is issued here — otherwise
    changing your password would silently sign you out of the tab you are
    standing in.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Current password is not correct"
        )

    try:
        profile_service.validate_new_password(
            payload.new_password, payload.current_password
        )
    except ProfileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()
    await db.refresh(current_user)
    return Token(
        access_token=create_access_token(
            subject=str(current_user.id), token_version=current_user.token_version
        )
    )


# Everything an account owns. A test asserts this matches the models, so
# adding a table with a `user_id` fails the suite until it is listed here —
# the one protection an explicit list needs.
OWNED_BY_USER = (
    Submission,
    DailyPlan,
    WeeklyReport,
    Reminder,
    Revision,
    SyncState,
    Interview,
    LeetCodeProfile,
    EmailChangeRequest,
)


@router.post("/me/sessions/revoke", response_model=Token)
async def revoke_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sign out everywhere else, keeping the tab this was pressed in.

    The same `token_version` bump a password change performs, exposed on its
    own: the mechanism already existed, it simply had no way to be used
    deliberately. Worth having because the realistic case is a college machine
    you walked away from, where you know the password is fine and it is the
    session you want gone.

    A replacement token is issued so the caller stays signed in. Logging
    somebody out of the device they are holding, to protect them from a device
    they are not, would be a strange bargain.
    """
    current_user.token_version = (current_user.token_version or 0) + 1
    await db.commit()
    await db.refresh(current_user)
    return Token(
        access_token=create_access_token(
            subject=str(current_user.id), token_version=current_user.token_version
        )
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    payload: DeleteAccount,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete the account and everything belonging to it.

    Gated on the current password. A borrowed session must not be able to
    destroy an account — this is the one action with no undo, so it asks for
    the one thing a borrowed session does not have.

    The child rows are removed explicitly rather than left to the database.
    Half these tables were created without `ON DELETE CASCADE`, so a plain
    delete fails on a foreign key; and being explicit means the list of what
    an account *is* can be read here rather than inferred from eight schema
    definitions. The cost is that a new table must be added to this list — so
    it deletes by user id in one transaction, and a missed table would leave
    rows that reference nobody rather than silently surviving in a live board.
    """
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Password is not correct"
        )

    user_id = current_user.id
    for table in OWNED_BY_USER:
        await db.execute(delete(table).where(table.user_id == user_id))

    await db.delete(current_user)
    await db.commit()
    log.info("account %s deleted at its owner's request", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _live_request(
    db: AsyncSession, user_id: int, now: datetime
) -> EmailChangeRequest | None:
    """The newest request that could still be completed, if there is one."""
    return await db.scalar(
        select(EmailChangeRequest)
        .where(
            EmailChangeRequest.user_id == user_id,
            EmailChangeRequest.consumed_at.is_(None),
            EmailChangeRequest.expires_at > now,
            EmailChangeRequest.attempts < email_change_service.MAX_ATTEMPTS,
        )
        .order_by(EmailChangeRequest.created_at.desc())
        .limit(1)
    )


def _pending_out(pending: EmailChangeRequest, now: datetime) -> PendingEmailChange:
    return PendingEmailChange(
        new_email=pending.new_email,
        expires_at=pending.expires_at,
        attempts_left=email_change_service.MAX_ATTEMPTS - pending.attempts,
        resend_in_seconds=email_change_service.seconds_until_resend(
            pending.created_at, now
        ),
    )


@router.get("/me/email/pending", response_model=PendingEmailChange | None)
async def read_pending_email_change(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lets the UI come back to the code entry screen after a reload."""
    now = _now()
    pending = await _live_request(db, current_user.id, now)
    return _pending_out(pending, now) if pending else None


@router.post(
    "/me/email/request",
    response_model=PendingEmailChange,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_email_change(
    payload: RequestEmailChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a move to a new address, sending a code there to prove ownership.

    Nothing on the user row changes here. The address only moves once the code
    comes back, which is the whole point of the round trip.
    """
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is not correct")

    now = _now()

    # Resending is the same call again, so the cooldown lives here rather than
    # on a separate endpoint that would need the same checks anyway.
    existing = await _live_request(db, current_user.id, now)
    if existing:
        wait = email_change_service.seconds_until_resend(existing.created_at, now)
        if wait and existing.new_email == payload.new_email.lower().strip():
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"A code was just sent. Try again in {wait} seconds.",
            )

    try:
        # Compared case-insensitively, because a stored "Foo@x.com" would
        # otherwise let the same address be registered twice.
        taken = bool(
            await db.scalar(
                select(User.id).where(
                    func.lower(User.email)
                    == email_change_service.normalise_email(payload.new_email),
                    User.id != current_user.id,
                )
            )
        )
        target = email_change_service.validate_target(
            payload.new_email, current_user.email, taken
        )
    except EmailChangeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    code = email_change_service.generate_code()
    subject, body = email_change_service.verification_message(
        code, current_user.display_name
    )

    try:
        await send_mail(target, subject, body)
    except MailError as exc:
        # A code that never arrives is a dead end, so this one has to be loud
        # rather than logged and forgotten.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Could not send the verification email. Try again shortly.",
        ) from exc

    # Written only after the send succeeds: a stored request whose code went
    # nowhere would just sit there blocking retries until it expired.
    pending = EmailChangeRequest(
        user_id=current_user.id,
        new_email=target,
        code_hash=hash_password(code),
        expires_at=email_change_service.expiry_for(now),
        created_at=now,
    )
    db.add(pending)
    await db.commit()
    await db.refresh(pending)

    # Best effort: the old address hearing about this is a safety net, not a
    # precondition, so a bounce here must not fail a valid request.
    notice_subject, notice_body = email_change_service.notice_message(
        target, current_user.display_name
    )
    try:
        await send_mail(current_user.email, notice_subject, notice_body)
    except MailError:
        log.warning("Could not notify %s of an email change", current_user.email)

    return _pending_out(pending, now)


@router.post("/me/email/verify", response_model=UserOut)
async def verify_email_change(
    payload: VerifyEmailChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = _now()

    pending = await db.scalar(
        select(EmailChangeRequest)
        .where(
            EmailChangeRequest.user_id == current_user.id,
            EmailChangeRequest.consumed_at.is_(None),
        )
        .order_by(EmailChangeRequest.created_at.desc())
        .limit(1)
    )
    if pending is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No email change is waiting to be confirmed"
        )

    try:
        email_change_service.check_usable(
            pending.expires_at, pending.attempts, pending.consumed_at, now
        )
    except EmailChangeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    if not verify_password(payload.code, pending.code_hash):
        # Counted and committed before the error goes out, so a client that
        # retries in a loop still runs out of attempts.
        pending.attempts += 1
        await db.commit()
        left = email_change_service.MAX_ATTEMPTS - pending.attempts
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"That code is not correct. {left} attempt{'' if left == 1 else 's'} left."
            if left
            else "That code is not correct. Start again.",
        )

    # Re-checked at the last moment: the address may have been registered by
    # someone else in the ten minutes since the code went out.
    taken = await db.scalar(
        select(User.id).where(
            func.lower(User.email) == pending.new_email, User.id != current_user.id
        )
    )
    if taken:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "That email address is no longer available"
        )

    current_user.email = pending.new_email
    pending.consumed_at = now
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/me/email/pending", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_email_change(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = _now()
    pending = await _live_request(db, current_user.id, now)
    if pending:
        # Marked consumed rather than deleted, so the attempt history stays
        # visible if a takeover ever needs reconstructing.
        pending.consumed_at = now
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw = await file.read()

    try:
        profile_service.validate_upload(file.content_type, len(raw))
        image, mime = profile_service.normalise_avatar(raw)
    except ProfileError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    current_user.avatar = image
    current_user.avatar_mime = mime
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/me/avatar")
async def read_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.has_avatar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo uploaded")

    # Selected on its own rather than through the relationship: the column is
    # deferred, and touching it on the loaded object would trigger a lazy load
    # that an async session cannot service.
    image = await db.scalar(select(User.avatar).where(User.id == current_user.id))
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No photo uploaded")

    return Response(
        content=image,
        media_type=current_user.avatar_mime,
        # Private: this is served per-user behind a token, so a shared cache
        # must never hold on to it.
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.delete("/me/avatar", response_model=UserOut)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.avatar = None
    current_user.avatar_mime = None
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/codeforces-handle", response_model=UserOut)
async def set_codeforces_handle(
    payload: SetCodeforcesHandle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.codeforces_handle = payload.codeforces_handle
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/leetcode-repo", response_model=UserOut)
async def set_leetcode_repo(
    payload: SetLeetcodeRepo,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.leetcode_repo = payload.leetcode_repo
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/leetcode-username", response_model=UserOut)
async def set_leetcode_username(
    payload: SetLeetcodeUsername,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.leetcode_username = payload.leetcode_username.strip()
    await db.commit()
    await db.refresh(current_user)
    return current_user
