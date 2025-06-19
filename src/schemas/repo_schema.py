from pydantic import BaseModel

class RepoAnalysisRequest(BaseModel):
    repo_url: str

class RepoImportRequest(BaseModel):
    project_name: str
    repo_url: str