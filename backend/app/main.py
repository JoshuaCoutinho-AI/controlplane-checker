from fastapi import FastAPI
app = FastAPI(title="ControlPlane Checker")

@app.get("/health")
def health():
    return {"status": "ok"}
