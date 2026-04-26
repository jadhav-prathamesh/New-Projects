ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT 'raw';
ALTER TABLE documents ADD COLUMN reflection_score REAL DEFAULT 1.0;
ALTER TABLE documents ADD COLUMN parent_id TEXT;
ALTER TABLE documents ADD COLUMN source_ids TEXT;

CREATE INDEX IF NOT EXISTS idx_documents_doc_type
  ON documents (doc_type);

CREATE INDEX IF NOT EXISTS idx_documents_date_created
  ON documents (date_created);

