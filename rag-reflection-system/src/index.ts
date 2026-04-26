import { handleIngest } from "./handlers/ingest";
import { handleSearch } from "./handlers/search";
import { json } from "./utils/http";
import type { Env } from "./types/env";

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return json({
        name: "rag-reflection-system",
        status: "ok",
        endpoints: {
          ingest: "POST /ingest",
          search: "POST /search",
        },
      });
    }

    if (request.method === "POST" && url.pathname === "/ingest") {
      return handleIngest(request, env, ctx);
    }

    if (request.method === "POST" && url.pathname === "/search") {
      return handleSearch(request, env);
    }

    return json({ error: "Not found" }, 404);
  },
};

