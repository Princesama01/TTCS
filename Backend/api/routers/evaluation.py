import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from evaluation.run_evaluation import run_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

RESULTS_PATH = Path(__file__).parent.parent.parent / "evaluation" / "results" / "evaluation_results.json"
CHUNKING_RESULTS_PATH = Path(__file__).parent.parent.parent / "evaluation" / "results" / "chunking_experiment_results.json"
CHUNKING_REPORT_PATH = Path(__file__).parent.parent.parent / "evaluation" / "results" / "chunking_report.md"


@router.get("")
async def get_evaluation_results():
    if not RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Chua co ket qua danh gia. Goi POST /api/evaluation/run de tao ket qua.",
        )
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


@router.post("/run")
async def run_evaluation_now():
    try:
        result = run_evaluation()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")
    return {"success": True, "result": result}


@router.get("/chunking")
async def get_chunking_results():
    if not CHUNKING_RESULTS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Chua co ket qua chunking. Goi POST /api/evaluation/chunking/run de tao ket qua.",
        )
    return json.loads(CHUNKING_RESULTS_PATH.read_text(encoding="utf-8"))


@router.get("/chunking/report")
async def get_chunking_report():
    if not CHUNKING_REPORT_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Chua co bao cao chunking. Goi POST /api/evaluation/chunking/run truoc.",
        )
    return {"success": True, "report": CHUNKING_REPORT_PATH.read_text(encoding="utf-8")}


@router.post("/chunking/run")
async def run_chunking_evaluation_now():
    try:
        from evaluation.chunking_experiment import run_chunking_experiment

        result = run_chunking_experiment()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chunking evaluation failed: {exc}")
    return {"success": True, "result": result}
