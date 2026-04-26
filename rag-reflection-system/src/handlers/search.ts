import { readNumber, resolveEmbeddingModel, resolveReflectionModel } from "../config/models";
import { boostSearchMatches, buildContext } from "../engines/search";
import { error, json, readJson } from "../utils/http";
import type { SearchPayload } from "../types/api";
import type { Env } from "../types/env";

type VectorizeQueryOptions = {
  topK: number;
  returnMetadata: "all";
  filter?: Record<string, string>;
};

export async function handleSearch(request: Request, env: Env): Promise<Response> {
  const payload = await readJson<SearchPayload>(request);
  const query = payload.query?.trim();

  if (!query) {
    return error("`query` is required for search.");
  }

  const embeddingResponse = await env.AI.run(resolveEmbeddingModel(env), {
    text: [query],
  });

  const vector = (embeddingResponse as { data?: Array<{ embedding?: number[] }> }).data?.[0]?.embedding;
  if (!Array.isArray(vector) || vector.length === 0) {
    return error("Query embedding failed.", 500);
  }

  const options: VectorizeQueryOptions = {
    topK: payload.topK && payload.topK > 0 ? payload.topK : readNumber(env.TOP_K, 6),
    returnMetadata: "all",
  };

  if (payload.filters?.doc_type) {
    options.filter = { doc_type: payload.filters.doc_type };
  }

  const searchResult = await env.VECTORIZE.query(vector, options);
  const matches = boostSearchMatches(searchResult.matches ?? []);
  const includeAnswer = payload.includeAnswer ?? true;

  let answer = "";
  if (includeAnswer && matches.length > 0) {
    const context = buildContext(matches.slice(0, 4));
    const answerResponse = await env.AI.run(resolveReflectionModel(env), {
      messages: [
        {
          role: "system",
          content:
            "Answer using only the provided context. If the answer is not supported, say that the context does not contain enough information.",
        },
        {
          role: "user",
          content: `Question: ${query}\n\nContext:\n${context}`,
        },
      ],
    });

    answer = extractText(answerResponse);
  }

  return json({
    query,
    answer,
    matches,
  });
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

    return (maybeResponse.response ?? maybeResponse.result?.response ?? "").trim();
  }

  return "";
}

