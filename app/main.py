from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="StayMatch AI Service",
)

app.include_router(router)