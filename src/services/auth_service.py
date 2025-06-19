from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.auth_handler import (
    verify_password,
    get_password_hash,
    create_tokens,
    refresh_tokens
)
from src.schemas.user_schema import UserCreate, UserLogin, RefreshTokenRequest
from src.models.main_model import User, Repository
from src.services.auth_handler import get_token_from_header, decode_token
from src.database import get_session
from sqlalchemy import select
from src.services.auth_handler import decode_token
import uuid

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def register_user(self, user_data: UserCreate) -> dict:
        existing_user = await self.session.execute(
            select(User).where(
                (User.username == user_data.username)
            )
        )
        if existing_user.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered",
            )
            
        hash_pasw = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hash_pasw=hash_pasw
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        tokens = create_tokens(str(user.id))
        return {
            "user": user,
            "tokens": tokens
        }

    async def authenticate_user(self, credentials: UserLogin) -> dict:
        user = await self.session.execute(
            select(User).where(User.username == credentials.username)
        )
        user = user.scalars().first()
        
        if not user or not verify_password(credentials.password, user.hash_pasw):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect username or password',
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        tokens = create_tokens(str(user.id))
        return {
            "user": user,
            "tokens": tokens,
        }
        
    async def refresh_access_token(self, token_data:RefreshTokenRequest) -> dict:
        tokens = refresh_tokens(token_data.refresh_token)
        return tokens
    
    async def get_current_user(self, token_data: str) -> dict:
        try:
            payload = decode_token(token_data)
            user_id = uuid.UUID(payload.get("sub"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "username": user.username,
            "email": user.email,
            "id": user.id
        }
    
async def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)