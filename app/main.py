from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="Sudan Mining Hub MVP")

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Sudan Mining Hub API"}
