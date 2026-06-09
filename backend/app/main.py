import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from fastapi.staticfiles import StaticFiles
import os

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="The Secretariat Chatbot",
    description="API for The Secretariat Chatbot",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/")
def read_root():
    return {"status": "ok", "service": "RAG Chatbot API"}


# Create the folder if it doesn't exist
os.makedirs("docs/processed", exist_ok=True)

# Mount the folder so files are accessible via URL
app.mount("/files", StaticFiles(directory="docs/processed"), name="processed_files")