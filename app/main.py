from fastapi import FastAPI

from app.api import auth, endpoints

app = FastAPI()
app.include_router(endpoints.router)
app.include_router(auth.router)
