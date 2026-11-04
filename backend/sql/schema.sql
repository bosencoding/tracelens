-- TraceLens v2 schema (SQLite, idempotent). One file: data/tracelens.db
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS evidence (
  id            TEXT PRIMARY KEY,
  filename      TEXT NOT NULL,
  byte_size     INTEGER NOT NULL,
  mime_type     TEXT NOT NULL,
  sha256        TEXT NOT NULL,
  stored_path   TEXT NOT NULL,
  uploaded_at   TEXT NOT NULL,
  verdict_label TEXT NOT NULL,
  verdict_text  TEXT NOT NULL,
  confidence    REAL NOT NULL,
  camera_guess  TEXT NOT NULL,
  encoder_guess TEXT NOT NULL,
  width         INTEGER NOT NULL,
  height        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS signatures (
  evidence_id      TEXT PRIMARY KEY REFERENCES evidence(id) ON DELETE CASCADE,
  exif_json        TEXT NOT NULL,
  qtable_luma      TEXT NOT NULL,
  qtable_chroma    TEXT NOT NULL,
  fingerprint_hex  TEXT NOT NULL,
  subsampling      TEXT NOT NULL,
  restart_interval INTEGER,
  huffman_tables   INTEGER NOT NULL,
  app_markers      TEXT NOT NULL,
  edit_traces      TEXT NOT NULL,
  components       TEXT NOT NULL,
  computed_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_cameras (
  id               TEXT PRIMARY KEY,
  label            TEXT NOT NULL,
  make             TEXT NOT NULL,
  model            TEXT NOT NULL,
  encoder          TEXT NOT NULL,
  note             TEXT NOT NULL,
  qtable_luma      TEXT NOT NULL,
  qtable_chroma    TEXT NOT NULL,
  fingerprint_hex  TEXT NOT NULL,
  subsampling      TEXT NOT NULL,
  what_if          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
  evidence_id  TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
  rank         INTEGER NOT NULL,
  reference_id TEXT NOT NULL REFERENCES reference_cameras(id),
  similarity   REAL NOT NULL,
  explanation  TEXT NOT NULL,
  PRIMARY KEY (evidence_id, rank)
);

CREATE INDEX IF NOT EXISTS evidence_uploaded_idx ON evidence(uploaded_at DESC);
