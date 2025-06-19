from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status
from pathlib import Path
from src.services.github_service import GitHubService, GitHubWebhookService
from src.utils.doc_generator import generate_docs_for_group
from src.utils.dependency_analyzer import DependencyAnalyzer
from src.services.ai_service import AIService
from src.models.main_model import Repository, FileGroup
from sqlalchemy.ext.asyncio import AsyncSession
import uuid, os, shutil, asyncio, json, tempfile, zipfile
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from src.redis import redis_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLONE_DIR = PROJECT_ROOT / "storage/repo_clones"
ENCRYPTED_DIR_ROOT = PROJECT_ROOT / "storage/docs"

class RepositoryService:
    def __init__(self, db_session: AsyncSession, github_token: str):
        self.session = db_session
        self.github_service = GitHubService(github_token)
        self.git_webhook = GitHubWebhookService(github_token)
        self.ai_service = AIService()
        self.executor = ProcessPoolExecutor(max_workers=2)
        
    async def process_repository(self, repo_url: str, user_id: uuid.UUID) -> Dict:
        try: 
            repo_info = await self.github_service.get_repo_info(repo_url)
            CLONE_DIR.mkdir(exist_ok=True)
            temp_dir = await self.github_service.clone_repository(repo_url, str(CLONE_DIR / str(user_id)))
            
            if not os.path.exists(temp_dir):
                raise HTTPException(status_code=500, detail="Failed to clone repository")

            repo_id = uuid.uuid4()
            
            asyncio.create_task(self._process_repository_background(repo_id, temp_dir, repo_url, user_id, repo_info))
            
            return {
                "status": "processing",
                "message": "Генерация была начата. В скором времени мы сообщим о ее готовности.",
                "repo_id": repo_id,
                "user_id": str(user_id)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Repository processing failed: {str(e)}")
    
    async def process_zip_repository(self, zip_path: str, user_id: uuid.UUID) -> Dict:
        try:
            temp_dir = tempfile.mkdtemp(prefix="repo_zip_")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            repo_id = uuid.uuid4()
            
            asyncio.create_task(
                self._process_repository_background(
                    repo_id,
                    temp_dir,
                    f"ZIP Archive: {os.path.basename(zip_path)}",
                    user_id,
                    {"name": os.path.basename(zip_path)}
                )
            )
            
            return {
                "status": "processing",
                "message": "Генерация документации начата",
                "repo_id": str(repo_id),
                "user_id": str(user_id)
            }
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный ZIP архив"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка обработки архива: {str(e)}"
            )
    
    async def _process_repository_background(self, repo_id: uuid.UUID,  temp_dir: str, repo_url: str, user_id: uuid.UUID, repo_info: Dict):
        try:
            analyzer = DependencyAnalyzer(temp_dir)
            file_groups, file_details = analyzer.analyze_repository()
            
            docs_dir = ENCRYPTED_DIR_ROOT / str(user_id) / str(repo_id)
            
            await self._generate_documentation(temp_dir, file_groups, file_details, docs_dir)
            await self._save_repo_to_db(repo_id, user_id, repo_info['name'], repo_url, str(docs_dir), file_groups)
            
            await self._notify_user(user_id, repo_id)
        except Exception as e:
            print(f"Error processing repository: {e}")
        finally:
            if not repo_url.startswith("zip:"):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _notify_user(self, user_id: uuid.UUID, repo_id: uuid.UUID):
        """Отправляет уведомление пользователю через WebSocket"""
        message = {
            "status": "ready",
            "repo_id": str(repo_id),
            "user_id": str(user_id),
            "docs_url": f"/docs/{user_id}/{repo_id}"
        }
        await redis_service.publish(f"user:{user_id}:ws", json.dumps(message))
    
    async def _generate_documentation(
        self, 
        repo_path: str, 
        file_groups: List[Set[str]], 
        file_details: Dict, 
        docs_dir: Path
    ):
        docs_dir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        
        tasks = []
        for group_idx, group in enumerate(file_groups, 1):
            if not group:
                continue 

            group_task = loop.run_in_executor(
                self.executor,
                partial(
                    generate_docs_for_group,
                    group_idx,
                    list(group),
                    repo_path,
                    file_details,
                    docs_dir
                )
            )
            tasks.append(group_task)
        
        await asyncio.gather(*tasks)
        
    async def _save_repo_to_db(
        self, repo_id: uuid.UUID, user_id: uuid.UUID,
        repo_name: str, repo_url: str, docs_dir: str, 
        file_groups: List[List[str]]
    ):
        try:
            repo = Repository(
                id=repo_id,
                user_id=user_id,
                name=repo_name,
                ssh_url=repo_url,
                encrypted_dir_path=docs_dir
            )
            self.session.add(repo)
            await self.session.flush()
            
            for group_idx, group_files in enumerate(file_groups, 1):
                group_id = uuid.uuid4()
                file_group = FileGroup(
                    id=group_id,
                    repo_id=repo_id,
                    name=f"Group {group_idx}"
                )
                self.session.add(file_group)
            
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    def _find_file_group(self, docs_dir: Path, file_path: str) -> Optional[Path]:
        file_name = os.path.basename(file_path)
        doc_pattern = f"{file_name}.md"

        for group_dir in docs_dir.glob("group_*"):
            if (group_dir / doc_pattern).exists():
                return group_dir
        return None
        
    async def _get_repository_by_url(self, repo_url: str, user_id: uuid.UUID) -> Optional[Repository]:
        from sqlalchemy.future import select
        
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
            
        result = await self.session.execute(
            select(Repository).where(
                Repository.ssh_url == repo_url,
                Repository.user_id == user_id
            ).limit(1)
        )
        return result.scalars().first()
    
async def delete_repository(session, user_id: str, repo_id: str):
    """Полное удаление репозитория"""

    from sqlalchemy import delete
    
    try:
        docs_path = os.path.join(ENCRYPTED_DIR_ROOT, str(user_id), str(repo_id))
        if os.path.exists(docs_path):
            shutil.rmtree(docs_path)
            
        await session.execute(
            delete(FileGroup).where(FileGroup.repo_id == repo_id)
        )
        await session.execute(
            delete(Repository).where(Repository.id == repo_id)
        )
        
        await session.commit()
    except Exception as e:
        print("Error delete repository in db: ", str(e))
        session.rollback()
