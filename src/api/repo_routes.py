from fastapi import APIRouter, Depends, HTTPException, status, Header, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates
from src.services.auth_handler import decode_token
from src.services.repo_service import RepositoryService, ENCRYPTED_DIR_ROOT
from src.database import get_session
from src.models.main_model import GitHubAuth
from src.redis import redis_service
from sqlalchemy import select
from src.schemas.repo_schema import RepoAnalysisRequest
import uuid, tempfile, os, shutil, zipfile, asyncio

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/analyze")
async def analyze_repository(
    request: RepoAnalysisRequest,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_session)
):
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user_id = await _get_authenticated_user(authorization)
        github_token = await _get_github_token(user_id, db)
        
        if not github_token:
            print("GitHub account not linked")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account not linked"
            )

        service = RepositoryService(db, github_token)
        return await service.process_repository(request.repo_url, user_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Repository processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repository processing failed: {str(e)}"
        )
        
@router.post("/import")
async def import_repository(
    repoFile: UploadFile = File(...),
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_session)
):
    """Импортирует репозиторий из ZIP архива"""
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user_id = await _get_authenticated_user(authorization)
        
        if not repoFile.filename.lower().endswith(('.zip', '.rar', '.7z')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Поддерживаются только ZIP, RAR и 7ZIP архивы"
            )
        
        temp_dir = tempfile.mkdtemp(prefix="repo_zip_")
        zip_path = os.path.join(temp_dir, repoFile.filename)
        
        with open(zip_path, "wb") as f:
            content = await repoFile.read()
            f.write(content)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный ZIP архив"
            )
        
        service = RepositoryService(db, None) 
        repo_id = uuid.uuid4()
        
        asyncio.create_task(
            service._process_repository_background(
                repo_id, 
                temp_dir, 
                f"ZIP Archive: {repoFile.filename}", 
                user_id, 
                {"name": repoFile.filename}
            )
        )
        
        return {
            "status": "processing",
            "message": "Генерация документации начата",
            "repo_id": str(repo_id),
            "user_id": str(user_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обработки архива: {str(e)}"
        )

@router.post("/cache-url")
async def cache_repo_url(
    request: RepoAnalysisRequest,
    authorization: str = Header(None),
):
    """Кэширует URL репозитория перед аутентификацией через GitHub"""
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user_id = await _get_authenticated_user(authorization)
        await redis_service.set_key(f"user:{user_id}:repo_url", request.repo_url, expire=600)
        return {"status": "success", "message": "Repo URL cached"}
    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cache repo URL: {str(e)}"
        )
        
@router.websocket("/ws/docs-status/{user_id}")
async def websocket_docs_status(websocket: WebSocket, user_id: uuid.UUID):
    await websocket.accept()
    redis_key = f"user:{user_id}:ws"
    
    try:
        await redis_service.set_key(redis_key, str(websocket), expire=3600)
        
        pubsub = await redis_service.subscribe(f"user:{user_id}:ws")
        
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            if message:
                await websocket.send_text(message['data'])
                
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        await redis_service.delete_key(redis_key)

async def _get_authenticated_user(authorization: str) -> uuid.UUID:
    """Проверяет аутентификацию и возвращает ID пользователя"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization[7:]
    payload = decode_token(token)
    return uuid.UUID(payload.get("sub"))

async def _get_github_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    """Получает GitHub токен пользователя"""
    result = await db.execute(select(GitHubAuth).where(GitHubAuth.user_id == user_id))
    github_auth = result.scalars().first()
    
    if not github_auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account not linked"
        )
    
    return github_auth.access_token