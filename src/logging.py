import logging
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any
import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging():
    """Настройка логгера для приложения"""
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = JSONFormatter()
    
    error_handler = logging.FileHandler(LOG_DIR / "errors.log")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    
    info_handler = logging.FileHandler(LOG_DIR / "app.log")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(error_handler)
    logger.addHandler(info_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Обработчик HTTP исключений с логированием"""
    extra = {
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": request.url.path,
        "method": request.method,
        "headers": dict(request.headers),
    }
    
    if exc.status_code >= 500:
        logger.error(f"Server error: {exc.detail}", extra=extra)
    elif exc.status_code >= 400:
        logger.warning(f"Client error: {exc.detail}", extra=extra)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)},
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик необработанных исключений"""
    extra = {
        "path": request.url.path,
        "method": request.method,
        "error_type": exc.__class__.__name__,
        "traceback": traceback.format_exc(),
    }
    
    logger.critical(f"Unhandled exception: {str(exc)}", extra=extra)
    
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

def log_request(request: Request, response: JSONResponse):
    """Логирование входящих запросов и ответов"""
    extra = {
        "path": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "request_headers": dict(request.headers),
        "response_headers": dict(response.headers),
    }
    
    if response.status_code >= 400:
        logger.warning(
            f"{request.method} {request.url.path} returned {response.status_code}",
            extra=extra
        )
    else:
        logger.info(
            f"{request.method} {request.url.path} returned {response.status_code}",
            extra=extra
        )

def log_error(message: str, extra: Dict[str, Any] = None):
    """Логирование ошибок с дополнительными данными"""
    logger.error(message, extra=extra or {})

def log_warning(message: str, extra: Dict[str, Any] = None):
    """Логирование предупреждений с дополнительными данными"""
    logger.warning(message, extra=extra or {})

def log_info(message: str, extra: Dict[str, Any] = None):
    """Логирование информационных сообщений"""
    logger.info(message, extra=extra or {})