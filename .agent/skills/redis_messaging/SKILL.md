---
name: Redis Messaging Patterns
description: Best practices for implementing Redis Streams in this project.
---

# Redis Messaging Patterns

This skill describes the standard patterns used in `agentic-mesh` for handling Redis Streams.

## 1. Stream Naming Convention
Streams should be prefixed with `doc.review.` for core review processes and `doc.suggestions.` for specialist agent outputs.

- Input Streams: `doc.review.<stage>` (e.g., `doc.review.grammar`)
- Output Streams: `doc.suggestions.<stage>` (e.g., `doc.suggestions.grammar`)
- Summary Stream: `doc.review.summary`

## 2. Consumer Groups
Consumer groups are essential for load balancing and avoiding duplicate processing.

- Always check if the group exists before creating (`xgroup_create`).
- Use `mkstream=True` to create the stream if it doesn't exist.
- Use `id="0"` to create the group from the beginning of the stream, or `"$"` for only new messages (depending on agent requirements). Default is "0".

## 3. Producing Messages (`xadd`)
Producers should add messages structured as flat dictionaries whenever possible to leverage Redis Stream's native field-value storage.

```python
# src/ingestion/producer.py or any agent
redis_client.xadd(STREAM_NAME, {
    "doc_id": "123",
    "chunk_id": "ab-1",
    "text": "sample text",
    "timestamp": datetime.now().isoformat()
})
```

## 4. Consuming Messages (`xreadgroup`)
Consumers use `xreadgroup` with blocking calls.

- **Block Duration**: 2000ms is standard.
- **Count**: Fetch in batches (e.g., `count=10`).
- **Processing Logic**:
    1.  Read messages (`>`).
    2.  Process each message.
    3.  ACKnkowledge (`xack`).

Pending messages (messages that were read but not ACKed due to crash) should be handled implementation-specific (e.g., periodic loop checking PEL via `xpending`).

## 5. Idempotency & Error Handling
- Since messages might be redelivered if a consumer crashes before ACK, ensure processing logic is idempotent.
- Catch exceptions inside the processing loop to prevent the consumer from crashing entirelly. Logs should clearly indicate which message ID failed.

## 6. Cleanup
Currently, streams are not automatically trimmed. In production, producers should use `maxlen` or `minid` in `xadd` to keep stream sizes manageable.

```python
redis_client.xadd(STREAM_NAME, data, maxlen=10000)
```
