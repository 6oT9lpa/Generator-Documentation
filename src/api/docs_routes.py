from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/{user_id}/{repo_id}")
async def get_documentation(request: Request, user_id: str, repo_id: str):
    docs_path = Path(f"storage/docs/{user_id}/{repo_id}")
    if not docs_path.exists():
        raise HTTPException(status_code=404, detail="Documentation not found")
    
    project_structure = []
    for group_dir in docs_path.glob("group_*"):
        group_files = []
        for md_file in group_dir.glob("*.md"):
            group_files.append({
                "name": md_file.stem,
                "path": f"{group_dir.name}/{md_file.name}"
            })
        project_structure.append({
            "group": group_dir.name,
            "files": group_files
        })
    
    return templates.TemplateResponse("docs.html", {
        "request": request,
        "project_structure": project_structure,
        "user_id": user_id,
        "repo_id": repo_id,
        "initial_file": project_structure[0]["files"][0]["path"] if project_structure else None
    })

@router.get("/content/{user_id}/{repo_id}/{file_path:path}")
async def get_documentation_content(user_id: str, repo_id: str, file_path: str):
    content_path = Path(f"storage/docs/{user_id}/{repo_id}/{file_path}")
    if not content_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(content_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"content": content}