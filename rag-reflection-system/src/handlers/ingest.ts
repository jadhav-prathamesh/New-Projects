import { readNumber, resolveEmbeddingModel } from "../config/models";
import { generateReflection } from "../engines/reflection";
import { error, json, readJson } from "../utils/http";
import type { IngestPayload } from "../types/api";
import type { Env, StoredDocument } from "../types/env";

export async function handleIngest(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  const payload = await readJson<IngestPayload>(request);
  const content = payload.content?.trim();

  if (!content) {
    return error("`content` is required for ingestion.");
  }

  const id = payload.id?.trim() || crypto.randomUUID();
  const source = payload.source?.trim() || "manual_ingest";
  const createdAt = new Date().toISOString();

  const embeddingResponse = await env.AI.run(resolveEmbeddingModel(env), {
    text: [content],
  });

  const vector = (embeddingResponse as { data?: Array<{ embedding?: number[] }> }).data?.[0]?.embedding;
  if (!Array.isArray(vector) || vector.length === 0) {
    return error("Embedding generation failed.", 500);
  }

  await env.VECTORIZE.upsert([
    {
      id,
      values: vector,
      metadata: {
        content: content.slice(0, 4000),
        source,
        doc_type: "raw",
        reflection_score: 1.0,
        date_created: createdAt,
      },
    },
  ]);

  await env.DB.prepare(
    `INSERT OR REPLACE INTO documents (
      id,
      content,
      source,
      date_created,
      doc_type,
      reflection_score,
      parent_id,
      source_ids
    ) VALUES (?, ?, ?, ?, 'raw', 1.0, NULL, NULL)`,
  )
    .bind(id, content, source, createdAt)
    .run();

  const relatedDocuments = await findRelatedDocuments(env, id, vector);
  ctx.waitUntil(generateReflection(env, content, relatedDocuments));

  return json({
    success: true,
    id,
    source,
    relatedDocumentCount: relatedDocuments.length,
    reflectionQueued: true,
  });
}

async function findRelatedDocuments(
  env: Env,
  currentId: string,
  embeddingValues: number[],
): Promise<StoredDocument[]> {
  const topK = readNumber(env.REFLECTION_SEARCH_K, 3);
  const queryResult = await env.VECTORIZE.query(embeddingValues, {
    topK,
    returnMetadata: "all",
  });

  const matches = queryResult.matches ?? [];
  const uniqueIds = [...new Set(matches.map((match) => match.id))].filter((id) => id !== currentId);
  if (uniqueIds.length === 0) {
    return [];
  }

  const placeholders = uniqueIds.map(() => "?").join(", ");
  const result = await env.DB.prepare(
    `SELECT id, content, source, date_created, doc_type, reflection_score, parent_id, source_ids
     FROM documents
     WHERE id IN (${placeholders})`,
  )
    .bind(...uniqueIds)
    .all<StoredDocument>();

  return result.results ?? [];
}
