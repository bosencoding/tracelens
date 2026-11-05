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