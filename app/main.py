from fastapi import FastAPI
import uvicorn
import logging
from datetime import datetime

# Import routers
from app.routers import chat, users

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("main")

# Initialize FastAPI app
app = FastAPI(
    title="Mental Health Support Bot API",
    description="API for mental health support bot with assessment tracking and crisis intervention",
    version="1.0.0"
)

# Include routers
app.include_router(chat.router, prefix="/api")
app.include_router(users.router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"status": "online", "message": "Mental Health Support Bot API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)