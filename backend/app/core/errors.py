"""Error handling for the application"""
from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Custom API error exception"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def api_error_handler(request: Request, exc: ApiError):
    """Handle API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
