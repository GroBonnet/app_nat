from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import router

app = FastAPI(
    title="FFN Stats API",
    version="0.1.0",
    description="Consultation des résultats de natation (compétitions, épreuves, "
                "nageurs) avec filtres.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["système"])
def health():
    return {"status": "ok"}
