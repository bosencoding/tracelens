export interface ExifField {
  tag: string
  value: string | null
  state: 'ok' | 'missing' | 'inconsistent'
}

export interface ExifReport {
  fields: ExifField[]
  make: string | null
  model: string | null
  lens: string | null
  software: string | null
  serial: string | null
  datetime_original: string | null
  has_thumbnail: boolean
  makernote_present: boolean
}

export interface QTables {
  luma: number[]
  chroma: number[]
}

export interface EditTrace {
  key: string
  label: string
  detected: boolean
  detail: string
}

export interface EncoderInfo {
  guess: string
  confidence: 'kuat' | 'sedang' | 'lemah'
  subsampling: string
  restart_interval: number | null
  huffman_tables: number
  app_markers: string[]
  note: string
}

export interface ComponentScore {
  key: string
  label: string
  score: number
  weight: number
  contribution: number
  reason: string
}

export interface Signature {
  evidence_id: string
  exif: ExifReport
  qtable: QTables
  fingerprint_hex: string
  encoder: EncoderInfo
  edit_traces: EditTrace[]
  components: ComponentScore[]
  computed_at: string
}

export interface Match {
  reference_id: string
  label: string
  make: string
  model: string
  encoder: string
  note: string
  similarity: number
  rank: number
  explanation: string
}

export interface AppSettings {
  max_upload_mb: number
  db_file: string
  db_path: string | null
  evidence_count: number
  app_version: string
}

export interface Evidence {
  id: string
  filename: string
  byte_size: number
  mime_type: string
  sha256: string
  uploaded_at: string
  verdict_label: 'kuat' | 'sedang' | 'lemah' | 'tidak dapat dipastikan'
  verdict_text: string
  confidence: number
  camera_guess: string
  encoder_guess: string
  width: number
  height: number
}

export interface EvidenceDetail extends Evidence {
  signature: Signature
  matches: Match[]
}

export interface ReferenceCamera {
  id: string
  label: string
  make: string
  model: string
  luma_table: number[]
  chroma_table: number[]
  subsampling: string
  note: string
}

export interface ReferenceList {
  cameras: ReferenceCamera[]
}
