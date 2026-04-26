import { readNumber, resolveEmbeddingModel, resolveReflectionModel } from "../config/models";
import type { Env, StoredDocument } from "../types/env";

export async function generateReflection(
  env: Env,
  content: string,
  relatedDocuments: StoredDocument[],
): Promise<void> {
  const relatedContext = relatedDocuments
    .map((document, index) => {
      return `Document ${index + 1} (${document.source}): ${document.content}`;
    })
    .join("\n");

  const prompt = [
    "You are a knowledge reflection assistant.",
    "Read the new content and the related context, then write one concise insight that captures the most important reusable knowledge.",
    "Focus on durable understanding, patterns, constraints, and practical implications.",
    "Return plain text only.",
    "",
    "New content:",
    content,
    "",
    "Related context:",
    relatedContext || "No related context available.",
  ].join("\n");

  const reflectionResponse = await env.AI.run(resolveReflectionModel(env), {
    messages: [
      {
        role: "user",
        content: prompt,
      },
    ],
  });

  const reflectionText = extractText(reflectionResponse);
  if (!reflectionText) {
    return;
  }

  const reflectionId = `reflection_${crypto.randomUUID()}`;
  const embeddingValues = await embedText(env, reflectionText);
  if (embeddingValues.length === 0) {
    return;
  }
  const sourceIds = relatedDocuments.map((document) => document.id).join(",");
  const sourceLabel = relatedDocuments.map((document) => document.source).join(", ") || "reflection";
  const createdAt = new Date().toISOString();

  await env.VECTORIZE.upsert([
    {
      id: reflectionId,
      values: embeddingValues,
      metadata: {
        content: reflectionText,
        source: sourceLabel,
        doc_type: "reflection",
        reflection_score: 1.2,
        date_created: createdAt,
        source_ids: sourceIds,
      },
    },
  ]);

  await env.DB.prepare(
    `INSERT INTO documents (
      id,
      content,
      source,
      date_created,
      doc_type,
      reflection_score,
      parent_id,
      source_ids
    ) VALUES (?, ?, ?, ?, 'reflection', 1.2, NULL, ?)`,
  )
    .bind(reflectionId, reflectionText, sourceLabel, createdAt, sourceIds)
    .run();

  await maybeConsolidateReflections(env);
}

async function maybeConsolidateReflections(env: Env): Promise<void> {
  const threshold = readNumber(env.CONSOLIDATION_THRESHOLD, 3);
  const unconsolidated = await env.DB.prepare(
    `SELECT id, content, source, date_created, doc_type, reflection_score, parent_id, source_ids
     FROM documents reflections
     WHERE reflections.doc_type = 'reflection'
       AND NOT EXISTS (
         SELECT 1
         FROM documents summaries
         WHERE summaries.doc_type = 'summary'
           AND instr(',' || IFNULL(summaries.source_ids, '') || ',', ',' || reflections.id || ',') > 0
       )
     ORDER BY reflections.date_created DESC
     LIMIT ?`,
  )
    .bind(threshold)
    .all<StoredDocument>();

  const reflections = unconsolidated.results ?? [];
  if (reflections.length < threshold) {
    return;
  }

  const summaryPrompt = [
    "Create a higher-level summary that consolidates these reflections into durable knowledge.",
    "Combine related ideas, remove repetition, and keep the result short and actionable.",
    "Return plain text only.",
    "",
    ...reflections.map((reflection, index) => `Reflection ${index + 1}: ${reflection.content}`),
  ].join("\n");

  const summaryResponse = await env.AI.run(resolveReflectionModel(env), {
    messages: [
      {
        role: "user",
        content: summaryPrompt,
      },
    ],
  });

  const summaryText = extractText(summaryResponse);
  if (!summaryText) {
    return;
  }

  const summaryId = `summary_${crypto.randomUUID()}`;
  const embeddingValues = await embedText(env, summaryText);
  if (embeddingValues.length === 0) {
    return;
  }
  const sourceIds = reflections.map((reflection) => reflection.id).join(",");
  const sourceLabel = `summary_of_${reflections.length}_reflections`;
  const createdAt = new Date().toISOString();

  await env.VECTORIZE.upsert([
    {
      id: summaryId,
      values: embeddingValues,
      metadata: {
        content: summaryText,
        source: sourceLabel,
        doc_type: "summary",
        reflection_score: 1.5,
        date_created: createdAt,
        source_ids: sourceIds,
      },
    },
  ]);

  await env.DB.prepare(
    `INSERT INTO documents (
      id,
      content,
      source,
      date_created,
      doc_type,
      reflection_score,
      parent_id,
      source_ids
    ) VALUES (?, ?, ?, ?, 'summary', 1.5, NULL, ?)`,
  )
    .bind(summaryId, summaryText, sourceLabel, createdAt, sourceIds)
    .run();
}

async function embedText(env: Env, text: string): Promise<number[]> {
  const embeddingResponse = await env.AI.run(resolveEmbeddingModel(env), {
    text: [text],
  });

  const rawVector = (embeddingResponse as { data?: Array<{ embedding?: number[] }> }).data?.[0]?.embedding;
  return Array.isArray(rawVector) ? rawVector : [];
}

function extractText(response: unknown): string {
  if (typeof response === "string") {
    return response.trim();
  }

  if (response && typeof response === "object") {
    const maybeResponse = response as {
      response?: string;
      result?: { response?: string };
    };

    const text = maybeResponse.response ?? maybeResponse.result?.response ?? "";
    return text.trim();
  }

  return "";
}
