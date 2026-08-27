"""
Lancement :
  uv run uvicorn api.main:app --reload

Documentation auto :
  http://localhost:8000/docs      ← Swagger UI
  http://localhost:8000/redoc     ← ReDoc
"""
import uvicorn
from pyfiglet import print_figlet

if __name__ == "__main__":
    print_figlet("APP NATATION BACKEND", font="standard", width=200, colors="0;191;255:")
    uvicorn.run("src.main:app", port=8000, reload=True)
