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

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetCodeforcesHandle(BaseModel):
    codeforces_handle: str


class SetLeetcodeUsername(BaseModel):
    leetcode_username: str = Field(min_length=1, max_length=100)


class SetLeetcodeRepo(BaseModel):
    # "owner/repo" of a LeetHub-synced GitHub repository.
    leetcode_repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
