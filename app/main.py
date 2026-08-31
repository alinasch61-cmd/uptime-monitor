from api import auth, endpoints
from fastapi import FastAPI

app = FastAPI()
app.include_router(endpoints.router)
app.include_router(auth.router)

@app.get("/")
async def get_root():
    return {"message": "Start"}