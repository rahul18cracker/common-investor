from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.core.errors import ApiError, api_error_handler
from app.core.logging import init_logging

app = FastAPI(title="Common Investor API", version="0.1.0")

# Configure CORS — restrict to actual methods/headers used by the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

init_logging(settings.log_level)
app.include_router(v1_router, prefix="/api/v1")
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
