CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  source TEXT NOT NULL,
  date_created TEXT NOT NULL
);

