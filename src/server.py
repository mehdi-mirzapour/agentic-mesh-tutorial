from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import asyncio
import redis.asyncio as aioredis
import json
import os
import shortuuid
import time
from src.core.redis_client import (
    STREAM_DOC_TASKS, STREAM_REVIEW_SUMMARY, 
    STREAM_DOC_GRAMMAR, STREAM_DOC_CLARITY, STREAM_DOC_TONE, STREAM_DOC_STRUCTURE
)

app = FastAPI()

# Redis Clients
redis_client = aioredis.from_url(
    f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}",
    encoding="utf-8", decode_responses=True
)

@app.post("/analyze")
async def analyze_document(text: str):
    """
    Simulate uploading a document for analysis.
    Chunk text (dummy chunking) and push to TASKS stream.
    """
    doc_id = f"doc-{shortuuid.uuid()}"
    
    # Process text into simple chunks (by line for demo)
    chunks = [c.strip() for c in text.split('\n') if c.strip()]
    if not chunks:
        chunks = [text] # If single line

    print(f"Received doc {doc_id} with {len(chunks)} chunks.")

    for i, chunk_text in enumerate(chunks):
        chunk_id = f"p-{i}"
        payload = {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "text": chunk_text,
            "language": "en",
            "timestamp": time.time()
        }
        await redis_client.xadd(STREAM_DOC_TASKS, payload)

    return {"doc_id": doc_id, "status": "processing", "chunks": len(chunks)}


@app.get("/stream")
async def stream_events():
    """
    SSE endpoint to push updates from Redis Streams to the browser.
    Listens to ALL relevant streams to visualize the flow.
    """
    async def event_generator():
        # Subscribe to all streams we care about
        streams = {
            STREAM_DOC_TASKS: '$',     # Coordinator Input
            STREAM_DOC_GRAMMAR: '$',   # Specialist Inputs
            STREAM_DOC_CLARITY: '$',
            STREAM_DOC_TONE: '$',
            STREAM_DOC_STRUCTURE: '$',
            STREAM_REVIEW_SUMMARY: '$' # Final Output
        }

        while True:
            try:
                # Poll Redis Streams (XREAD)
                # This could be more efficient with XREAD non-blocking loop per stream
                # For demo, simple read works.
                messages = await redis_client.xread(streams, count=1, block=5000)
                
                if messages:
                    for stream, msgs in messages:
                        # Update last ID for next poll
                        streams[stream] = msgs[-1][0] 
                        
                        for msg_id, data in msgs:
                            # Construct event for frontend
                            event_type = "unknown"
                            if stream == STREAM_DOC_TASKS: event_type = "coordinator_job"
                            elif stream in [STREAM_DOC_GRAMMAR, STREAM_DOC_CLARITY, STREAM_DOC_TONE, STREAM_DOC_STRUCTURE]: event_type = "specialist_job"
                            elif stream == STREAM_REVIEW_SUMMARY: event_type = "aggregator_result"
                            
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": event_type,
                                    "stream": stream,
                                    "id": msg_id,
                                    "content": data
                                })
                            }
                
                # Heartbeat to keep connection alive
                yield {"event": "ping", "data": "keep-alive"}
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"SSE Error: {e}")
                await asyncio.sleep(1)

    return EventSourceResponse(event_generator())

# Serve static files (HTML/JS/CSS)
app.mount("/", StaticFiles(directory="src/web", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
