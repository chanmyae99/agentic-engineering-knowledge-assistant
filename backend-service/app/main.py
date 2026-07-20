from fastapi import FastAPI

app = FastAPI(
    title="Agentic Engineering Knowledge Assistant",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Backend Service Running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }