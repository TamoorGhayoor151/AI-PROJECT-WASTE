"""
FastAPI backend
-----------------
Exposes the multi-agent pipeline over HTTP.

Run locally with:
    uvicorn api.main:app --reload --port 8000

Test with:
    curl -X POST http://localhost:8000/analyze \
      -H "Content-Type: application/json" \
      -d '{"description": "2.5 tons mixed concrete rubble with embedded rebar, from Site B demolition"}'
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

from orchestrator.graph import run_pipeline, run_pipeline_batch

app = FastAPI(
    title="Construction Waste Recovery API",
    description="Multi-agent system for analyzing C&D waste and generating recovery plans.",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    description: str


class BatchAnalyzeRequest(BaseModel):
    descriptions: List[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not req.description or not req.description.strip():
        raise HTTPException(status_code=400, detail="description must not be empty")
    try:
        result = run_pipeline(req.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    return result


@app.post("/analyze/batch")
def analyze_batch(req: BatchAnalyzeRequest):
    if not req.descriptions:
        raise HTTPException(status_code=400, detail="descriptions must not be empty")
    try:
        result = run_pipeline_batch(req.descriptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
