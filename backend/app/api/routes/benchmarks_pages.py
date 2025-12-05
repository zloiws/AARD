"""
Page routes for benchmark web interface
"""
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.database import get_db
from app.services.benchmark_service import BenchmarkService

router = APIRouter(tags=["benchmarks_pages"])


@router.get("/benchmarks", response_class=HTMLResponse)
async def benchmarks_index(request: Request, db: Session = Depends(get_db)):
    """Benchmark tasks selection page"""
    return templates.TemplateResponse(
        "benchmarks/index.html",
        {
            "request": request
        }
    )


@router.get("/benchmarks/results", response_class=HTMLResponse)
async def benchmarks_results(
    request: Request,
    ids: str = Query(None, description="Comma-separated result IDs"),
    db: Session = Depends(get_db)
):
    """Benchmark results page"""
    return templates.TemplateResponse(
        "benchmarks/results.html",
        {
            "request": request,
            "result_ids": ids.split(",") if ids else []
        }
    )


@router.get("/benchmarks/comparison", response_class=HTMLResponse)
async def benchmarks_comparison(request: Request, db: Session = Depends(get_db)):
    """Benchmark model comparison page"""
    return templates.TemplateResponse(
        "benchmarks/comparison.html",
        {
            "request": request
        }
    )

