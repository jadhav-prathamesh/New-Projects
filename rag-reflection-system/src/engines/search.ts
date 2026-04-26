import type { SearchMatch } from "../types/api";

type VectorizeMatch = {
  id: string;
  score: number;
  metadata?: Record<string, unknown>;
};

export function boostSearchMatches(matches: VectorizeMatch[]): SearchMatch[] {
  return matches
    .map((match) => {
      const metadata = match.metadata ?? {};
      const docType = String(metadata.doc_type ?? "raw");
      const reflectionScore = asNumber(metadata.reflection_score, 1);
      const baseScore = asNumber(match.score, 0);

      let boostedScore = baseScore;
      if (docType === "reflection") {
        boostedScore *= 1.25;
      } else if (docType === "summary") {
        boostedScore *= 1.4;
      }

      boostedScore *= reflectionScore;

      return {
        id: match.id,
        score: Number(boostedScore.toFixed(6)),
        content: String(metadata.content ?? ""),
        source: String(metadata.source ?? "unknown"),
        docType,
        reflectionScore,
      };
    })
    .sort((left, right) => right.score - left.score);
}

export function buildContext(matches: SearchMatch[]): string {
  return matches
    .map((match, index) => {
      return [
        `Source ${index + 1}`,
        `Document ID: ${match.id}`,
        `Type: ${match.docType}`,
        `Origin: ${match.source}`,
        `Content: ${match.content}`,
      ].join("\n");
    })
    .join("\n\n");
}

function asNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

