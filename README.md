# PDF Reader — local PDF RAG reader

PDF Reader is a private, local-first PDF reader and chat app following the supplied architecture: offline extraction and semantic chunking, then query rewriting, hybrid retrieval, reranking, memory-aware response generation, and page citations. Existing examples in the repository remain unchanged.

## Architecture

- **FastAPI** (`backend/app`) provides REST endpoints, background ingestion, and SQLite metadata/chat persistence. All RAG services are consolidated in `backend/app/services/__init__.py`.
- **PDF pipeline**: PyMuPDF extracts page-indexed text; optional OCR uses Tesseract. Sentence-transformer embeddings group nearby sentences at configurable semantic boundaries; child passages link to parent sections and retain page/heading metadata.
- **Retrieval**: searchable child passages and citation metadata persist in ChromaDB. Local BM25 keyword search and cosine vector search are fused with Reciprocal Rank Fusion, then optionally reordered by a Sentence Transformers Cross-Encoder. Specific questions must have a meaningful keyword match or pass the configured cosine-distance threshold.
- **Answering**: OpenAI-compatible calls go only to LM Studio. The LLM rewrites follow-ups and periodically updates a rolling summary. The final prompt includes the original question, reference-only memory, child passages, parent context, and source metadata. PDF text is treated as untrusted input. When retrieval finds no relevant passage, the API returns a fixed abstention without calling the LLM.
- **Storage**: PDFs and parent sections under `storage/pdfs`, Chroma at `storage/chroma`, and SQLite at `storage/app.sqlite3`.
- **React/Vite UI**: document library, browser PDF viewer, and chat. Clicking a source opens the PDF at the cited page. Text highlighting is not implemented.

## Requirements

Python 3.11+ recommended; Node.js 20+. Install LM Studio, download/load a compatible Llama model, and start its OpenAI-compatible local server (usually `http://127.0.0.1:1234/v1`). Configure the model identifier in `.env`. The default `lm-studio` API key is a local placeholder.

Embedding and reranker models run locally and download on first use. Pre-cache their model weights for fully offline first-time use. OCR is optional; install Tesseract and set `OCR_ENABLED=true`.

## Run locally (PowerShell)

1. Backend:

   ```powershell
   cd FinalChatBot/backend
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   # Edit .env if needed
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. Frontend in another terminal:

   ```powershell
   cd FinalChatBot/frontend
   npm install
   npm run dev
   ```

3. Open `http://localhost:5173`, upload a PDF, wait for **Ready**, select it, and chat. API docs: `http://127.0.0.1:8000/docs`.

The first embedding/reranker use can take time while weights download. LM Studio must remain running for query rewriting, generation, and summaries. If it is unavailable, the backend returns a 503 with setup guidance.

## Configuration

See `backend/.env.example` for model/API settings, local storage paths, upload size, semantic chunking threshold, chunk bounds/overlap, retrieval top-k values and maximum cosine distance, RRF constant, reranking depth, recent-message limit, summary interval, context budget, and OCR flag. Chunk bounds currently use whitespace word-count estimates so they are independent of the embedding tokenizer; adjust `MAX_CHUNK_TOKENS` for the loaded model context window.

## API

- Documents: `POST/GET /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/status`, `GET /api/documents/{id}/file`, `DELETE /api/documents/{id}`
- Conversations: `POST/GET /api/conversations`, `GET/PATCH/DELETE /api/conversations/{id}`
- Messages: `GET/POST /api/conversations/{id}/messages`, `POST /api/conversations/{id}/clear`
- Health: `GET /api/health`

Uploads are size-limited and SHA-256 deduplicated. Chat rejects selected PDFs while ingestion is incomplete. No authentication is configured; bind locally and keep the server private.

## Tests and retrieval evaluation

After installing dependencies: `cd backend; pytest`. Included tests cover PDF page extraction, chunk parent-child links, embedding calls, Chroma metadata, BM25, hybrid RRF, reranking, query rewriting, summary updates, citation context, and conversation API CRUD. For sample retrieval inspection:

```powershell
python evaluate_retrieval.py --document-id YOUR_ID --question "What are the eligibility rules?" --question "When is the deadline?"
```

A live end-to-end run requires LM Studio and local model weights. The frontend uses the browser's PDF viewer for page navigation; it does not highlight matched text or stream tokens.


