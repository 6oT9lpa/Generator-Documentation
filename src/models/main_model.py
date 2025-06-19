import uuid
from src.models.base_model import Base
from sqlalchemy import String, ForeignKey, UUID, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "user"
    
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    email: Mapped[str] = mapped_column(
        String(255),  
        unique=True,
        nullable=False,
        index=True
    )
    hash_pasw: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
class GitHubAuth(Base):
    __tablename__ = "github_auth"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
        unique=True
    )
    github_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )
    access_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    token_type: Mapped[str] = mapped_column(
        String(50),
        nullable=True
    )
    scope: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )

class Repository(Base):
    __tablename__ = "repository"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id"), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        index=True
    )
    ssh_url: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    encrypted_dir_path: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    webhook_configured: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    webhook_id: Mapped[int] = mapped_column (
        Integer,
        nullable=True
    )
    
class FileGroup(Base):
    __tablename__ = "file_group"
    
    repo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository.id"), 
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=True
    )
