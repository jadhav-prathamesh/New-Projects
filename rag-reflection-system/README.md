# Self-Learning RAG System With Knowledge Reflection

This folder contains a new Cloudflare Worker project modeled on the architecture from the freeCodeCamp article:

- D1 stores documents and reflection metadata
- Vectorize stores embeddings for retrieval
- Workers AI creates embeddings, reflections, summaries, and grounded answers
- Background reflection runs after ingestion so the knowledge base gets better over time

## Project Structure

```text
rag-reflection-system/
|-- migrations/
|   |-- 001_init.sql
|   `-- 002_add_reflection_fields.sql
|-- src/
|   |-- config/
|   |   `-- models.ts
|   |-- engines/
|   |   |-- reflection.ts
|   |   `-- search.ts
|   |-- handlers/
|   |   |-- ingest.ts
|   |   `-- search.ts
|   |-- types/
|   |   |-- api.ts
|   |   `-- env.ts
|   |-- utils/
|   |   `-- http.ts
|   `-- index.ts
|-- .gitignore
|-- package.json
|-- README.md
|-- tsconfig.json
`-- wrangler.toml
```

## What This Build Does

### `POST /ingest`

1. Accepts a document payload with `content`, optional `id`, and optional `source`
2. Creates an embedding with Workers AI
3. Stores the raw content in D1 and Vectorize
4. Finds related documents
5. Queues a background reflection job

### Reflection pipeline

1. Reads the newly ingested content plus semantically related documents
2. Generates a short reusable insight
3. Saves that insight as a `reflection` document with a higher retrieval weight
4. Periodically consolidates several reflections into a `summary`

### `POST /search`

1. Embeds the incoming question
2. Queries Vectorize
3. Boosts `reflection` and `summary` entries during ranking
4. Optionally asks Workers AI to answer only from the retrieved context

## Example requests

### Ingest a document

```bash
curl -X POST http://127.0.0.1:8787/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "id": "doc_api_design",
    "source": "engineering-notes",
    "content": "A stable API needs explicit versioning, strong contracts, and clear deprecation timelines."
  }'
```

### Search the knowledge base

```bash
curl -X POST http://127.0.0.1:8787/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How should we design stable APIs?",
    "includeAnswer": true
  }'
```

## Local setup

This machine does not currently have Node.js or Wrangler installed, so I created the full project structure and config, but I could not execute the Worker locally from here.

Once Node.js is installed, run:

```bash
cd "D:\VS\Projects\rag-reflection-system"
npm install
npx wrangler d1 create rag_reflection_db
npx wrangler vectorize create rag-reflection-index --dimensions=384 --metric=cosine
```

Update the generated database id in `wrangler.toml`, then apply migrations:

```bash
npx wrangler d1 migrations apply rag_reflection_db --local
npx wrangler dev
```

## Notes on alignment with the article

This implementation follows the article's ingestion, reflection, consolidation, and search flow, with two practical adjustments:

1. `source_ids` is stored explicitly so summary documents can track which reflections they were built from.
2. Search boosting is handled in the Worker after Vectorize returns matches, which keeps the ranking logic easy to inspect and adjust.
