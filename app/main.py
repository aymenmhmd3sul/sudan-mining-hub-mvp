from fastapi import FastAPI

app = FastAPI(
    title="Sudan Mining Hub API",
    version="0.1.0",
    description="Backend API for Sudan Mining Hub MVP"
)

@app.get("/")
def read_root():
    return {"status": "healthy", "service": "Sudan Mining Hub MVP"}
