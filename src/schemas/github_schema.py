from pydantic import BaseModel

class GitHubUser(BaseModel):
    id: int
    login: str
    name: str | None = None
    email: str | None = None

class GitHubAuthResponse(BaseModel):
    access_token: str
    token_type: str
    scope: str