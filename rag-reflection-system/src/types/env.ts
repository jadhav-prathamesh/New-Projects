export interface Env {
  AI: Ai;
  DB: D1Database;
  VECTORIZE: VectorizeIndex;
  EMBEDDING_MODEL?: string;
  REFLECTION_MODEL?: string;
  TOP_K?: string;
  REFLECTION_SEARCH_K?: string;
  CONSOLIDATION_THRESHOLD?: string;
}

export interface StoredDocument {
  id: string;
  content: string;
  source: string;
  date_created: string;
  doc_type: "raw" | "reflection" | "summary";
  reflection_score: number;
  parent_id: string | null;
  source_ids: string | null;
}

