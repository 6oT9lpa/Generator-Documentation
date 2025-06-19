from webbrowser import get
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.auth_routes import AuthService, get_auth_service
from src.database import get_session
from src.models.main_model import Repository
from sqlalchemy import select
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
async def user_profile(request: Request, db: AsyncSession = Depends(get_session)):
    user_id = request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    
    try:
        user_id = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    result = await db.execute(select(Repository).where(Repository.user_id == user_id))
    repos = result.scalars().all()
    
    repos_data = []
    for repo in repos:
        repos_data.append({
            "id": repo.id,
            "name": repo.name,
            "url": repo.ssh_url,
            "docs_url": f"/docs/{user_id}/{repo.id}",
            "created_at": repo.created_at.strftime("%Y-%m-%d") if repo.created_at else "N/A"
        })
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "repositories": repos_data,
        "user_id": str(user_id)
    })
    
@router.delete("/delete_repos/{repo_id}")
async def deelte_repository(
    repo_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    from src.services.repo_service import delete_repository
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    current_user = await auth_service.get_current_user(token)
    
    try:
        repo_id = uuid.UUID(repo_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid repository ID")
    
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.user_id == current_user["id"]
        )
    )
    repo = result.scalars().first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    await delete_repository(db, str(current_user["id"]), str(repo_id))
    return {"status": "success", "message": "Repository deleted successfully"}