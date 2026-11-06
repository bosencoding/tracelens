"""Reference cameras API: list all cameras with quantization tables."""

from __future__ import annotations

from fastapi import APIRouter

from . import db
from .models import BaseModel

router = APIRouter(prefix="/api/reference-cameras", tags=["reference"])


class ReferenceCameraOut(BaseModel):
    id: str
    label: str
    make: str
    model: str
    luma_table: list[int]
    chroma_table: list[int]
    subsampling: str
    note: str


class ReferenceListOut(BaseModel):
    cameras: list[ReferenceCameraOut]


class ReferenceStatsOut(BaseModel):
    total_cameras: int
    total_brands: int
    brands: list[str]
    auto_added_count: int
    manual_count: int


@router.get("", response_model=ReferenceListOut)
def list_reference_cameras() -> ReferenceListOut:
    """List all reference cameras with their quantization tables."""
    rows = db.list_reference_cameras()
    cameras = [
        ReferenceCameraOut(
            id=row["id"],
            label=row["label"],
            make=row["make"],
            model=row["model"],
            luma_table=row["luma_table"],
            chroma_table=row["chroma_table"],
            subsampling=row.get("subsampling", "4:2:0"),
            note=row.get("note", ""),
        )
        for row in rows
    ]
    return ReferenceListOut(cameras=cameras)


@router.get("/stats", response_model=ReferenceStatsOut)
def get_reference_stats() -> ReferenceStatsOut:
    """Get statistics about reference cameras."""
    # Total cameras
    total_row = db.row("SELECT COUNT(*) as count FROM reference_cameras")
    total_cameras = total_row["count"] if total_row else 0
    
    # Total brands
    brands_row = db.row("SELECT COUNT(DISTINCT make) as count FROM reference_cameras")
    total_brands = brands_row["count"] if brands_row else 0
    
    # List of brands
    brands_rows = db.rows("SELECT DISTINCT make FROM reference_cameras ORDER BY make")
    brands = [row["make"] for row in brands_rows]
    
    # Auto-added vs manual
    auto_row = db.row("SELECT SUM(is_auto_added) as count FROM reference_cameras")
    auto_added_count = auto_row["count"] if auto_row and auto_row["count"] else 0
    manual_count = total_cameras - auto_added_count
    
    return ReferenceStatsOut(
        total_cameras=total_cameras,
        total_brands=total_brands,
        brands=brands,
        auto_added_count=auto_added_count,
        manual_count=manual_count,
    )