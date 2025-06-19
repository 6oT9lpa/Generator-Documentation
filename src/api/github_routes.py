from fastapi import APIRouter, Depends, Request, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.github_service import GitHubAuthService, get_github_auth_service
from src.services.auth_handler import decode_token
from src.models.main_model import GitHubAuth
from fastapi.templating import Jinja2Templates
from src.database import get_session
from sqlalchemy import select
import uuid

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
templates = Jinja2Templates(directory="templates")

@router.get("/auth")
async def github_auth(service: GitHubAuthService = Depends(get_github_auth_service)):
    auth_url = await service.get_github_auth_url()
    return {"auth_url": auth_url}

@router.get("/callback")
async def github_callback(
    request: Request,
    code: str,
    service: GitHubAuthService = Depends(get_github_auth_service),
    authorization: str = Header(None)
):
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code"
        )
    
    try:
        github_data = await service.get_github_access_token(code)
        github_user = await service.get_github_user_info(github_data.access_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to authenticate with GitHub: {str(e)}"
        )
    
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = request.query_params.get("token")

    if not token:
        return templates.TemplateResponse("github_callback.html", {
            "request": request,
            "github_data": github_data.dict(),
            "github_user": github_user.dict(),
            "token": token
        })

    try:
        payload = decode_token(token)
        user_id = uuid.UUID(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        github_auth = await service.link_github_account(user_id, github_data, github_user)
        
        print(github_auth)
        
        return {
            "message": "GitHub account linked successfully",
            "github_user": github_user.dict(),
            "linked": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
@router.get("/status")
async def github_status(
    authorization: str = Header(None),
    service: GitHubAuthService = Depends(get_github_auth_service),
    session: AsyncSession = Depends(get_session)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization[7:]
    payload = decode_token(token)
    user_id = uuid.UUID(payload.get("sub"))
    
    result = await session.execute(
        select(GitHubAuth).where(GitHubAuth.user_id == user_id)
    )
    github_auth = result.scalars().first()
    
    if not github_auth:
        return {"linked": False}
    
    try:
        github_user = await service.get_github_user_info(github_auth.access_token)
        return {
            "linked": True,
            "github_user": github_user.dict()
        }
    except HTTPException:
        return {"linked": True, "details": "Could not fetch current user info"}
    
