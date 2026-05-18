"""Regulatory Monitor — Gazette of India, MoHFW, NABH updates."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.api.auth import assert_hospital_access, get_current_user, require_role
from app.models.database import RegulatoryUpdate, Staff, UserRole

router = APIRouter()


@router.get("/updates")
async def get_regulatory_updates(
    source: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    processed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get recent regulatory updates with optional filtering."""
    from datetime import timedelta
    
    query = db.query(RegulatoryUpdate)
    
    if source:
        query = query.filter(RegulatoryUpdate.source == source)
    if processed is not None:
        query = query.filter(RegulatoryUpdate.is_processed == processed)
    
    query = query.filter(
        RegulatoryUpdate.published_date >= datetime.utcnow() - timedelta(days=days)
    )
    
    updates = query.order_by(RegulatoryUpdate.published_date.desc()).limit(100).all()
    
    return {
        "total_updates": len(updates),
        "period_days": days,
        "updates": [{
            "id": u.id,
            "source": u.source,
            "type": u.update_type,
            "title": u.title,
            "summary": u.summary,
            "url": u.url,
            "published_date": u.published_date.isoformat() if u.published_date else None,
            "affected_areas": u.affected_areas,
            "is_processed": u.is_processed,
            "semantic_diff": u.semantic_diff,
            "impact_analysis": u.impact_analysis,
        } for u in updates]
    }


@router.post("/ingest")
async def trigger_regulatory_ingestion(
    current_user: Staff = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE_OFFICER])),
):
    """
    Trigger the Regulatory Ingestion Engine.
    Scrapes Gazette of India, MoHFW, and NABH for new updates.
    """
    from app.services.regulatory_ingestion import run_ingestion
    
    try:
        result = await run_ingestion()
        return {
            "status": "completed",
            "new_updates": result.get("new_updates", 0),
            "sources_checked": result.get("sources", []),
            "message": "Regulatory ingestion completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/search")
async def search_regulations(
    query: str = Query(..., min_length=3),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Semantic search across all ingested regulations using ChromaDB.
    This is the RAG engine in action.
    """
    from app.services.vector_store import search_regulations as vector_search
    
    try:
        results = vector_search(query, limit=limit)
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/impact/{hospital_id}")
async def get_regulatory_impact(
    hospital_id: str,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
):
    """
    assert_hospital_access(current_user, hospital_id)

    Analyze which recent regulatory changes impact this specific hospital.
    Based on hospital type, location, and compliance areas.
    """
    from app.models.database import Hospital
    
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Get recent unprocessed updates
    updates = db.query(RegulatoryUpdate).filter(
        RegulatoryUpdate.is_processed == False
    ).order_by(RegulatoryUpdate.published_date.desc()).limit(50).all()
    
    impacted = []
    for update in updates:
        # Simple relevance matching
        relevance = 0
        affected = update.affected_areas or []
        
        # FCRA relevance
        if hospital.fcra_number and "fcra" in affected:
            relevance += 30
        
        # NABH relevance
        if hospital.nabh_accreditation_id and "nabh" in affected:
            relevance += 25
        
        # State relevance
        if hospital.state and update.full_text and hospital.state.lower() in (update.full_text or "").lower():
            relevance += 20
        
        # General healthcare relevance
        if any(area in affected for area in ["bmw", "dpdp", "clinical_establishment"]):
            relevance += 15
        
        if relevance > 0:
            impacted.append({
                "update_id": update.id,
                "title": update.title,
                "source": update.source,
                "published_date": update.published_date.isoformat() if update.published_date else None,
                "relevance_score": relevance,
                "affected_areas": affected,
                "impact_analysis": update.impact_analysis,
                "actions_required": update.compliance_actions_required,
            })
    
    # Sort by relevance
    impacted.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return {
        "hospital_id": hospital_id,
        "hospital_name": hospital.name,
        "impacted_updates": len(impacted),
        "updates": impacted[:20],
        "recommendation": "Review high-relevance updates immediately. Assign compliance officers for action items."
    }
