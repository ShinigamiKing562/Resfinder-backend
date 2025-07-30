from fastapi import FastAPI
from app.routers import resfinder
from app.routers import phastest

app = FastAPI()

# Register routers
app.include_router(resfinder.router, prefix="/api", tags=["ResFinder"])
#app.include_router(phastest.router, prefix="/api", tags=["Phastest"])

@app.get("/")
def read_root():
    return {"message": "Bacteriophage backend is running"}
