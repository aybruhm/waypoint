"""
Document RAG (Retrieval-Augmented Generation) pipeline — AI workflow.

Prerequisites:
    - Waypoint API running at http://localhost:9654

Usage:
    uv run python -m sdk.examples.document_rag

This example demonstrates:
    - @waypoint.checkpoint instance decorator form (vs the standalone @checkpoint form)
    - Encapsulating workflow steps in a class bound to a specific Waypoint instance
    - cache=True on the embedding step (most expensive — LLM API call per chunk)
    - Creating a second RAGPipeline with a new Waypoint instance for crash recovery

Crash recovery scenario:
    If the process crashes after build_index but before retrieve_context:
      - chunk_document     → cache=True, replayed (deterministic chunking)
      - generate_embeddings → cache=True, replayed (no embedding API call — cost saved)
      - build_index        → cache=True, replayed (no recompute)
      - retrieve_context   → cache=False, runs fresh
      - generate_answer    → cache=False, fresh LLM call
"""

import asyncio
import hashlib

from sdk import Waypoint

WORKFLOW_ID = "document_rag"
API_BASE_URL = "http://localhost:9654/api/v1/"

SAMPLE_DOCUMENT = """
Waypoint is a durable workflow execution system built on event sourcing.
Every step in an agent workflow is recorded as an immutable event in an
append-only journal. When a workflow crashes, Waypoint replays the event log
to reconstruct state and resumes execution from the last successful checkpoint.
LLM API calls marked with cache=True are served from the journal on replay,
eliminating redundant LLM invocations and reducing costs significantly.
The system supports concurrent executions, each scoped to a unique execution_id.
Agents run as independent external processes and communicate with Waypoint over HTTP.
"""


class RAGPipeline:
    """
    RAG pipeline with each step bound to a specific Waypoint instance via
    the @waypoint.checkpoint instance decorator.

    Creating a new RAGPipeline with a different Waypoint instance gives an
    independent checkpoint routing — useful for crash recovery (see main()).
    """

    def __init__(self, waypoint: Waypoint) -> None:
        self.waypoint = waypoint
        self._register_steps()

    def _register_steps(self) -> None:
        wp = self.waypoint

        @wp.checkpoint("chunk_document", cache=True)
        async def chunk_document(text: str, chunk_size: int = 200) -> dict:
            """Split document into fixed-size word chunks. Deterministic — safe to cache."""
            words = text.split()
            chunks = []
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i : i + chunk_size]
                chunks.append(
                    {"id": i // chunk_size, "text": " ".join(chunk_words), "word_count": len(chunk_words)}
                )
            return {"chunks": chunks, "total_chunks": len(chunks)}

        @wp.checkpoint("generate_embeddings", cache=True)
        async def generate_embeddings(chunked: dict) -> dict:
            """
            Generate a vector for each chunk via the embedding API.
            Expensive — cache=True ensures this never re-runs on resume.
            """
            print(f"  Generating embeddings for {chunked['total_chunks']} chunks (expensive)...")
            await asyncio.sleep(0.1)
            embeddings = []
            for chunk in chunked["chunks"]:
                h = hashlib.md5(chunk["text"].encode()).hexdigest()
                vector = [int(h[i : i + 2], 16) / 255.0 for i in range(0, 16, 2)]
                embeddings.append({"chunk_id": chunk["id"], "vector": vector})
            return {"embeddings": embeddings, "dimensions": 8}

        @wp.checkpoint("build_index", cache=True)
        async def build_index(chunked: dict, embedded: dict) -> dict:
            """Pair chunks with their vectors to build the retrieval index."""
            embedding_map = {e["chunk_id"]: e["vector"] for e in embedded["embeddings"]}
            index = {
                chunk["id"]: {"text": chunk["text"], "vector": embedding_map[chunk["id"]]}
                for chunk in chunked["chunks"]
            }
            return {"index": index, "size": len(index)}

        @wp.checkpoint("retrieve_context", cache=False)
        async def retrieve_context(index_data: dict, query: str, top_k: int = 2) -> dict:
            """Retrieve the top-k most relevant chunks for the query. Query-dependent — no cache."""
            query_words = set(query.lower().split())
            scored = [
                (len(set(entry["text"].lower().split()) & query_words), chunk_id, entry["text"])
                for chunk_id, entry in index_data["index"].items()
            ]
            scored.sort(reverse=True)
            top_chunks = [text for _, _, text in scored[:top_k]]
            return {"context": top_chunks, "query": query, "retrieved": len(top_chunks)}

        @wp.checkpoint("generate_answer", cache=False)
        async def generate_answer(context_data: dict) -> dict:
            """Generate an answer using retrieved context. Fresh LLM call — no cache."""
            print("  Calling LLM to generate answer...")
            await asyncio.sleep(0.05)
            context_text = " | ".join(context_data["context"])
            return {
                "answer": f"Based on the documents: {context_text[:120]}...",
                "query": context_data["query"],
                "sources": context_data["retrieved"],
                "model": "gpt-4",
            }

        self.chunk_document = chunk_document
        self.generate_embeddings = generate_embeddings
        self.build_index = build_index
        self.retrieve_context = retrieve_context
        self.generate_answer = generate_answer

    async def run(self, document: str, query: str) -> dict:
        chunked = await self.chunk_document(text=document)
        print(f"  Step 1 (chunk_document,      cache=True):  {chunked['total_chunks']} chunks")

        embedded = await self.generate_embeddings(chunked=chunked)
        print(f"  Step 2 (generate_embeddings, cache=True):  {len(embedded['embeddings'])} vectors")

        index_data = await self.build_index(chunked=chunked, embedded=embedded)
        print(f"  Step 3 (build_index,         cache=True):  index size = {index_data['size']}")

        context_data = await self.retrieve_context(index_data=index_data, query=query)
        print(f"  Step 4 (retrieve_context,    cache=False): retrieved {context_data['retrieved']} chunks")

        answer = await self.generate_answer(context_data=context_data)
        print(f"  Step 5 (generate_answer,     cache=False): {answer['answer'][:80]}...")

        print(f"\n  Pipeline complete! Total steps: {self.waypoint.get_step_number()}")
        return answer


async def main():
    query = "How does Waypoint handle crash recovery?"

    # ── First run ────────────────────────────────────────────────────────────
    wp1 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID)
    execution_id = await wp1.create(
        initial_input={"query": query, "document_length": len(SAMPLE_DOCUMENT)}
    )
    print(f"Created execution: {execution_id}\n")

    print("--- FIRST RUN ---")
    pipeline1 = RAGPipeline(wp1)
    await pipeline1.run(SAMPLE_DOCUMENT, query)

    # ── Crash recovery ───────────────────────────────────────────────────────
    # A new Waypoint + RAGPipeline is created. resume() restores the state from
    # the journal. Steps 1-3 (cache=True) return their stored outputs without
    # re-running. Steps 4-5 run fresh — no embedding API call is made.
    print("\n--- CRASH RECOVERY ---")
    print("Resuming — generate_embeddings (cache=True) will NOT re-call the API.\n")

    wp2 = Waypoint(base_url=API_BASE_URL, workflow_id=WORKFLOW_ID)
    resume = await wp2.resume(execution_id)
    print(f"Resumed from step {resume.checkpoint_step}")
    print(f"Recovered state keys: {list(wp2.get_state().keys())}\n")

    pipeline2 = RAGPipeline(wp2)
    await pipeline2.run(SAMPLE_DOCUMENT, query)

    await wp1.aclose()
    await wp2.aclose()


if __name__ == "__main__":
    asyncio.run(main())
