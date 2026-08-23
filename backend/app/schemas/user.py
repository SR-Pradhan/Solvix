from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str | None = None
    codeforces_handle: str | None = None
    leetcode_repo: str | None = None
    leetcode_username: str | None = None
    # Read from the mime column, so serialising a user never loads the image.
    has_avatar: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetCodeforcesHandle(BaseModel):
    codeforces_handle: str


class SetLeetcodeUsername(BaseModel):
    leetcode_username: str = Field(min_length=1, max_length=100)


class DeleteAccount(BaseModel):
    """Deletion asks for the password: it is the one action with no undo."""

    password: str


class UpdateProfile(BaseModel):
    """A partial update: an omitted field is left alone.

    `display_name` is deliberately nullable, because clearing a name and not
    touching it are different intentions and both have to be expressible.
    Distinguished by `model_fields_set` rather than by the value.
    """

    display_name: str | None = None
    codeforces_handle: str | None = None
    leetcode_username: str | None = None
    # Editable here, not only on the dashboard's connect card: that card only
    # appears while the repo is unset, so a typo in it was unfixable.
    leetcode_repo: str | None = None


class RequestEmailChange(BaseModel):
    new_email: EmailStr
    # Required even though the caller is already authenticated: a borrowed
    # session should not be enough to take the account away from its owner.
    password: str


class VerifyEmailChange(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class PendingEmailChange(BaseModel):
    """What the UI needs to show the "check your inbox" state after a reload."""

    new_email: EmailStr
    expires_at: datetime
    attempts_left: int
    resend_in_seconds: int


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class SetLeetcodeRepo(BaseModel):
    # "owner/repo" of a LeetHub-synced GitHub repository.
    leetcode_repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
