import type { Env } from "../types/env";

const DEFAULT_EMBEDDING_MODEL = "@cf/baai/bge-small-en-v1.5";
const DEFAULT_REFLECTION_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";

const SUPPORTED_EMBEDDING_MODELS = new Set([
  "@cf/baai/bge-base-en-v1.5",
  "@cf/baai/bge-large-en-v1.5",
  "@cf/baai/bge-small-en-v1.5",
]);

const SUPPORTED_TEXT_MODELS = new Set([
  "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
  "@cf/meta/llama-3.1-8b-instruct",
  "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  "@cf/mistral/mistral-small-3.1-24b-instruct",
  "@cf/qwen/qwen2.5-coder-32b-instruct",
]);

export function resolveEmbeddingModel(env: Env): string {
  const selected = env.EMBEDDING_MODEL ?? DEFAULT_EMBEDDING_MODEL;
  return SUPPORTED_EMBEDDING_MODELS.has(selected) ? selected : DEFAULT_EMBEDDING_MODEL;
}

export function resolveReflectionModel(env: Env): string {
  const selected = env.REFLECTION_MODEL ?? DEFAULT_REFLECTION_MODEL;
  return SUPPORTED_TEXT_MODELS.has(selected) ? selected : DEFAULT_REFLECTION_MODEL;
}

export function readNumber(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

