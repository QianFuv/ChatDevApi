from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="ChatDev API",
    description="API for ChatDev project generation",
    version="1.0.0"
)

# Include routers
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)