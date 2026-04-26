export interface IngestPayload {
  id?: string;
  content?: string;
  source?: string;
}

export interface SearchPayload {
  query?: string;
  topK?: number;
  includeAnswer?: boolean;
  filters?: {
    doc_type?: "raw" | "reflection" | "summary";
  };
}

export interface SearchMatch {
  id: string;
  score: number;
  content: string;
  source: string;
  docType: string;
  reflectionScore: number;
}

