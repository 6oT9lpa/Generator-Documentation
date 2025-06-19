import httpx, uuid, os, shutil, tempfile, asyncio, subprocess
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.main_model import GitHubAuth, User
from src.schemas.github_schema import GitHubAuthResponse, GitHubUser
from src.database import Config, get_session
from sqlalchemy import select
from src.redis import redis_service
from typing import Dict
from urllib.parse import urlparse
import re
from datetime import datetime, timedelta

class GitHubAuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def get_github_auth_url(self) -> str:
        from config.config_app import Config
        
        params = {
            'client_id': Config.GITHUB_CLIENT_ID,
            "redirect_uri": Config.GITHUB_REDIRECT_URI,
            "scope": "repo",
            "state": uuid.uuid4()
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items() ])
        return f"{Config.GITHUB_AUTHORIZE_URL}?{query_string}"
    
    async def get_github_access_token(self, code: str) -> GitHubAuthResponse:
        from config.config_app import Config
        
        cached_data = await redis_service.get_github_code_data(code)
        if cached_data:
            await redis_service.delete_github_code(code)
            return GitHubAuthResponse(**cached_data)
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                Config.GITHUB_ACCESS_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": Config.GITHUB_CLIENT_ID,
                    "client_secret": Config.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": Config.GITHUB_REDIRECT_URI
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get access token from GitHub"
                )
            
            response_data = response.json()
            print("GitHub token exchange response:", response_data)
            
            await redis_service.store_github_code(code, response_data)
            
            return GitHubAuthResponse(**response_data)
        
    async def get_github_user_info(self, access_token: str) -> GitHubUser:
        from config.config_app import Config
        async with httpx.AsyncClient() as client:
            response = await client.get(
                Config.GITHUB_USER_API_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from GitHub"
                )
                
            return GitHubUser(**response.json())
        
    async def link_github_account(self, user_id: int, github_data: GitHubAuthResponse, github_user: GitHubUser) -> GitHubAuth:
        user = await self.session.execute(select(User).where(User.id == user_id))
        if not user.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        existing_auth = await self.session.execute(
            select(GitHubAuth).where(
                (GitHubAuth.user_id == user_id) |
                (GitHubAuth.github_id == str(github_user.id))
            )
        )
        existing_auth = existing_auth.scalars().first()
        
        if existing_auth:
            if existing_auth.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This GitHub account is already linked to another user"
                )
            
            existing_auth.access_token = github_data.access_token
            existing_auth.token_type = github_data.token_type
            existing_auth.scope = github_data.scope
        else:
            existing_auth = GitHubAuth(
                user_id=user_id,
                github_id=str(github_user.id),
                access_token=github_data.access_token,
                token_type=github_data.token_type,
                scope=github_data.scope
            )
            self.session.add(existing_auth)
        
        await self.session.commit()
        await self.session.refresh(existing_auth)
        return existing_auth
    
async def get_github_auth_service(session: AsyncSession = Depends(get_session)) -> GitHubAuthService:
    return GitHubAuthService(session)

class GitHubService:
    def __init__ (self, access_token: str):
        self.access_token = access_token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
    async def get_repo_info(self, repo_url: str) -> Dict:
        try:
            owner, repo_name = _parse_repo_url(repo_url)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/repos/{owner}/{repo_name}",
                    headers=self.headers
                )
                
                if response.status_code == 404:
                    print("Repository not found or access denied")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Repository not found or access denied"
                    )
                elif response.status_code != 200:
                    print(f"GitHub API error: {response.json()}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"GitHub API error: {response.json().get('message', 'Unknown error')}"
                    )
                
                return response.json()
        except HTTPException:
            raise
        except Exception as e:
            print(f"Failed to fetch repository info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch repository info: {str(e)}"
            )
            
    async def clone_repository(self, repo_url: str, clone_dir: str) -> str:
        temp_dir = tempfile.mkdtemp(prefix="repo_")
        auth_url = self._add_auth_to_repo_url(repo_url)

        def run_git_clone():
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', auth_url, temp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, run_git_clone)

            if result.returncode != 0:
                shutil.rmtree(temp_dir, ignore_errors=True)
                error_msg = result.stderr.strip()
                if "Repository not found" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Repository not found or access denied"
                    )
                raise RuntimeError(f"Git clone failed: {error_msg}")

            return temp_dir
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clone repository: {str(e)}"
            )
    
    def _add_auth_to_repo_url(self, repo_url: str) -> str:
        """Добавляет аутентификацию в URL репозитория"""
        
        if repo_url.startswith('git@'):
            return repo_url  
        
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        
        parsed = urlparse(repo_url)
        if not parsed.netloc:
            raise ValueError("Invalid repository URL")
        
        path = parsed.path.strip('/')
        return f"https://{self.access_token}:x-oauth-basic@github.com/{path}.git"
        
    async def _download_repo_contents(self, owner: str, repo_name: str, target_dir: str):
        """Рекурсивно скачивает содержимое репозитория"""
        
        async with httpx.AsyncClient() as client:
            await self._download_directory(owner, repo_name, "", target_dir, client)

    async def _download_directory(self, owner: str, repo_name: str, path: str, target_dir: str, client: httpx.AsyncClient):
        """Скачивает содержимое директории"""
        
        url = f"{self.api_base}/repos/{owner}/{repo_name}/contents/{path}" if path else f"{self.api_base}/repos/{owner}/{repo_name}/contents"
        
        response = await client.get(url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch contents for {path}")
        
        for item in response.json():
            item_path = os.path.join(target_dir, item['name'])
            
            if item['type'] == 'file':
                file_content = await client.get(item['download_url'], headers=self.headers)
                if file_content.status_code == 200:
                    with open(item_path, 'wb') as f:
                        f.write(file_content.content)
            elif item['type'] == 'dir':
                os.makedirs(item_path, exist_ok=True)
                await self._download_directory(owner, repo_name, item['path'], item_path, client)
    
class GitHubWebhookService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def create_repository_webhook(self, repo_url: str, webhook_url: str) -> Dict:
        """Создает webhook для репозитория"""
        
        owner, repo_name = _parse_repo_url(repo_url)
        
        payload = {
            "name": "web",
            "active": True,
            "events": ["push", "pull_request"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": Config.SECRET_KEY
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/hooks",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create webhook: {response.json()}"
                )
            
            return response.json()

    async def handle_webhook_event(self, event: Dict) -> Dict:
        """Обрабатывает событие от GitHub Webhook"""
        
        event_type = event.get("headers", {}).get("X-GitHub-Event")
        payload = event.get("body", {})
        
        if event_type == "push":
            return await self._handle_push_event(payload)
        elif event_type == "pull_request":
            return await self._handle_pull_request_event(payload)
        else:
            return {"status": "ignored", "event_type": event_type}

    async def _handle_push_event(self, payload: Dict) -> Dict:
        """Обрабатывает push событие"""
        repo_url = payload["repository"]["clone_url"]
        commits = payload.get("commits", [])
        modified_files = set()
        
        for commit in commits:
            modified_files.update(commit.get("added", []))
            modified_files.update(commit.get("modified", []))
            modified_files.update(commit.get("removed", []))
        
        supported_extensions = {'.py', '.js', '.ts', '.html', '.cpp', '.h', '.hpp', '.cs', '.rs', '.proto', '.css'}
        filtered_files = [
            f for f in modified_files
            if os.path.splitext(f)[1] in supported_extensions
        ]
        
        return {
            "event": "push",
            "repo_url": repo_url,
            "modified_files": filtered_files,
            "action": "update_docs"
        }

    async def _handle_pull_request_event(self, payload: Dict) -> Dict:
        """Обрабатывает pull request событие"""
        if payload["action"] not in ["opened", "synchronize", "reopened"]:
            return {"status": "ignored", "reason": "unrelated_action"}
        
        repo_url = payload["repository"]["clone_url"]
        pr_number = payload["number"]
        
        owner, repo_name = _parse_repo_url(repo_url)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_number}/files",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get PR files: {response.json()}"
                )
            
            files = response.json()
            supported_extensions = {'.py', '.js', '.ts', '.html', '.cpp', '.h', '.hpp', '.cs', '.rs', '.proto', '.css'}
            modified_files = [
                f["filename"] for f in files
                if os.path.splitext(f["filename"])[1] in supported_extensions
            ]
            
            return {
                "event": "pull_request",
                "repo_url": repo_url,
                "modified_files": modified_files,
                "action": "update_docs"
            }

def _parse_repo_url(repo_url: str) -> tuple:
    """Извлекает владельца и название репозитория из URL (HTTPS и SSH)"""

    # Обработка SSH-ссылки
    ssh_pattern = r'^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?$'
    ssh_match = re.match(ssh_pattern, repo_url)
    if ssh_match:
        owner = ssh_match.group('owner')
        repo_name = ssh_match.group('repo')
        return owner, repo_name

    # Обработка HTTPS-ссылки
    parsed = urlparse(repo_url)
    path_parts = parsed.path.strip('/').split('/')

    if parsed.netloc != 'github.com' or len(path_parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub repository URL"
        )

    owner = path_parts[0]
    repo_name = path_parts[1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]

    return owner, repo_name