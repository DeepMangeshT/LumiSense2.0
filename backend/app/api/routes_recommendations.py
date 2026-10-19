"""Recommendations and LumiSense Efficiency Score API endpoints.
"""
from fastapi import APIRouter, Query
from typing import List

from app.models.schemas import RecommendationItem, EfficiencyScoreResponse
from app.database import get_recommendations
from app.services.efficiency import calculate_efficiency_score

router = APIRouter()

@router.get("", response_model=List[RecommendationItem])
def get_energy_recommendations(limit: int = Query(20, ge=1, le=50)):
    """Returns rule-based energy-saving and comfort recommendations."""
    recs = get_recommendations(limit=limit)
    return [RecommendationItem(**r) for r in recs]

@router.get("/score", response_model=EfficiencyScoreResponse)
def get_lumisense_efficiency_score():
    """Returns the project-defined analytical LumiSense Efficiency Score (0-100)."""
    score_data = calculate_efficiency_score(source="real")
    return EfficiencyScoreResponse(**score_data)
