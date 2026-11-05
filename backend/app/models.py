from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    detail: str
    code: str
    fields: list[str] = Field(default_factory=list)


class ComponentScore(BaseModel):
    key: str
    label: str
    score: float
    weight: float
    contribution: float
    reason: str


class ExifField(BaseModel):
    tag: str
    value: str | None
    state: str  # ok | missing | inconsistent


class ExifReport(BaseModel):
    fields: list[ExifField]
    make: str | None = None
    model: str | None = None
    lens: str | None = None
    software: str | None = None
    serial: str | None = None
    datetime_original: str | None = None
    has_thumbnail: bool = False
    makernote_present: bool = False


class QTables(BaseModel):
    luma: list[int]
    chroma: list[int]


class EditTrace(BaseModel):
    key: str
    label: str
    detected: bool
    detail: str


class EncoderInfo(BaseModel):
    guess: str
    confidence: str  # kuat | sedang | lemah
    subsampling: str
    restart_interval: int | None = None
    huffman_tables: int = 0
    app_markers: list[str] = Field(default_factory=list)
    note: str


class SignatureOut(BaseModel):
    evidence_id: str
    exif: ExifReport
    qtable: QTables
    fingerprint_hex: str
    encoder: EncoderInfo
    edit_traces: list[EditTrace]
    components: list[ComponentScore]
    computed_at: str


class MatchOut(BaseModel):
    reference_id: str
    label: str
    make: str
    model: str
    encoder: str
    note: str
    similarity: float
    rank: int
    explanation: str


class AppSettings(BaseModel):
    max_upload_mb: int
    db_file: str
    db_path: str | None = None  # absolute path, loopback callers only
    evidence_count: int
    app_version: str


class SettingsPatch(BaseModel):
    max_upload_mb: int = Field(ge=1, le=500)


class EvidenceOut(BaseModel):
    id: str
    filename: str
    byte_size: int
    mime_type: str
    sha256: str
    uploaded_at: str
    verdict_label: str
    verdict_text: str
    confidence: float
    camera_guess: str
    encoder_guess: str
    width: int
    height: int


class EvidenceDetail(EvidenceOut):
    signature: SignatureOut
    matches: list[MatchOut]
