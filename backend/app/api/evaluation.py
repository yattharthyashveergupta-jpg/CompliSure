"""
Evaluation & Benchmarking Endpoints.
Executes experimental comparisons across safeguard modes and serves metric reports.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.schemas import (
    EvaluationReport,
    EvaluationRunRequest,
    EvaluationTestCase
)
from backend.app.models.database import get_db
from backend.app.services.evaluation_service import evaluation_service, BENCHMARK_DATASET

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarks"])


@router.post(
    "/run",
    response_model=EvaluationReport,
    status_code=status.HTTP_200_OK,
    summary="Run comparative evaluation across safeguard modes"
)
def run_evaluation_benchmark(
    request: Optional[EvaluationRunRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Executes the benchmark dataset through Baseline LLM, RAG, RAG + Evidence Threshold,
    and RAG + Verification, computing all compliance safety metrics.
    """
    modes = request.modes if request and request.modes else None
    threshold = request.threshold if request and request.threshold is not None else None

    report = evaluation_service.run_evaluation(
        modes=modes,
        threshold=threshold,
        db=db
    )
    return report


@router.get(
    "/results",
    response_model=EvaluationReport,
    summary="Get latest evaluation report"
)
def get_evaluation_results(db: Session = Depends(get_db)):
    """Retrieves the latest stored evaluation benchmark results or runs one if none exists."""
    latest = evaluation_service.get_latest_results(db)
    if not latest:
        # Run a fresh benchmark run if database has no stored results
        latest = evaluation_service.run_evaluation(db=db)
    return latest


@router.get(
    "/test-cases",
    response_model=List[EvaluationTestCase],
    summary="List all benchmark test cases"
)
def get_test_cases():
    """Returns the complete benchmark dataset of answerable, unanswerable, paraphrased, and ambiguous test cases."""
    return BENCHMARK_DATASET
