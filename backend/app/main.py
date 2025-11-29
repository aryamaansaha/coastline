from fastapi import FastAPI
from app.routers import localizer, trip, user

app = FastAPI()
app.include_router(localizer.router)
app.include_router(trip.router)
app.include_router(user.router)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}