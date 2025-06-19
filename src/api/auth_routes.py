from unittest import result
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.user_schema import (
UserCreate,
UserLogin,
Token,
RefreshTokenRequest
)
from src.services.auth_service import AuthService, get_auth_service

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    result = await auth_service.authenticate_user(user_data)
    return result["tokens"]

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    result = await auth_service.register_user(user_data)
    return result["tokens"]

@router.post("/refresh", response_model=Token)
async def refresh(token_data: RefreshTokenRequest, auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.refresh_access_token(token_data)

from fastapi import Header

@router.get("/me")
async def get_current_user(
    authorization: str = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.split(" ")[1]
    
    return await auth_service.get_current_user(token)

