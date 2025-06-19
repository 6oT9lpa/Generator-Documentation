import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.api.main_routes import router as main_router
from src.api.auth_routes import router as auth_router
from src.api.github_routes import router as github_router
from src.api.repo_routes import router as repo_router
from src.api.docs_routes import router as docs_router
from src.api.profile_routes import router as profile_router

def get_application() -> FastAPI:
    application = FastAPI(
        title='FastApi & AI Application',
        debug=True,
        version='beta 0.01'
    )
    application.include_router(main_router, tags=['main'])
    application.include_router(auth_router, prefix="/auth", tags=["auth"])
    application.include_router(github_router, prefix="/github", tags=["github"])
    application.include_router(repo_router, prefix="/repos", tags=["repo"])
    application.include_router(docs_router, prefix="/docs", tags=["docs"])
    application.include_router(profile_router, prefix="/profile", tags=["profile"])

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    application.mount("/static", StaticFiles(directory="static", html=True), name="static")
    
    return application

app = get_application()


if __name__ == "__main__":
    uvicorn.run()