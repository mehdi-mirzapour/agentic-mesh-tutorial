# Word Document Suggestion Mesh — Technical Specification

## 1. Objective

Create a distributed agent system to analyze Word (.docx) documents, provide grammar, clarity, tone, and structure suggestions, and deliver them back to a user interface or Word Add-in.

## 2. Architecture Overview

```
User Upload (.docx)
        ↓
Document Ingestion Service (Producer)
        ↓
Redis Stream: doc.review.tasks
        ↓
Coordinator Agent (Consumer + Producer)
        ↓
Redis Streams: doc.review.grammar, doc.review.clarity, doc.review.tone, doc.review.structure
        ↓
Specialist Agents (Consumer + Producer)
        ↓
Redis Streams: doc.suggestions.*
        ↓
Aggregator Agent (Consumer + Producer)
        ↓
Redis Stream: doc.review.summary
        ↓
UI / Word Add-in (Consumer)
```

## 3. Components & Responsibilities

| Component          | Role                | Streams (Produces)                                                            | Streams (Consumes)   | Notes                                                  |
| ------------------ | ------------------- | ----------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------ |
| Document Ingestion | Producer            | doc.review.tasks                                                              | None                 | Chunk .docx paragraphs, assign doc_id, chunk_id        |
| Coordinator Agent  | Consumer + Producer | doc.review.grammar, doc.review.clarity, doc.review.tone, doc.review.structure | doc.review.tasks     | Fan-out tasks to specialized streams                   |
| Grammar Agent      | Consumer + Producer | doc.suggestions.grammar                                                       | doc.review.grammar   | NLP/LLM-based grammar suggestions                      |
| Clarity Agent      | Consumer + Producer | doc.suggestions.clarity                                                       | doc.review.clarity   | Suggests sentence restructuring, simplifications       |
| Tone Agent         | Consumer + Producer | doc.suggestions.tone                                                          | doc.review.tone      | Ensures formal/informal tone alignment                 |
| Structure Agent    | Consumer + Producer | doc.suggestions.structure                                                     | doc.review.structure | Checks paragraph organization, headings                |
| Aggregator Agent   | Consumer + Producer | doc.review.summary                                                            | doc.suggestions.*    | Merges suggestions, resolves conflicts, ranks severity |
| UI / Word Add-in   | Consumer            | None                                                                          | doc.review.summary   | Presents suggestions to user, accepts/rejects changes  |

## 4. Redis Streams Specification

| Stream Name          | Purpose                      | Consumer Group    | Notes                               |
| -------------------- | ---------------------------- | ----------------- | ----------------------------------- |
| doc.review.tasks     | Chunked tasks from ingestion | coordinator-group | Single fan-out consumer group       |
| doc.review.grammar   | Grammar review tasks         | grammar-group     | Scalable consumers, retries via PEL |
| doc.review.clarity   | Clarity review tasks         | clarity-group     | Scalable consumers                  |
| doc.review.tone      | Tone review tasks            | tone-group        | Scalable consumers                  |
| doc.review.structure | Structure review tasks       | structure-group   | Scalable consumers                  |
| doc.suggestions.*    | Suggestions from specialists | aggregator-group  | Aggregator collects all             |
| doc.review.summary   | Final merged suggestions     | None              | Consumed by UI / Word Add-in        |

## 5. Chunking Strategy

* Split .docx by paragraph or N sentences per chunk
* Each chunk gets:

```
{
  "doc_id": "doc-123",
  "chunk_id": "p-5",
  "text": "...",
  "language": "en",
  "style": "formal"
}
```

* Chunk size tunable (2–5 sentences per chunk)

## 6. Agent Specifications

### Generic Agent Loop

1. Read message from input stream (XREADGROUP)
2. Process text (AI/NLP/LLM)
3. Write suggestion to output stream (XADD)
4. Acknowledge original message (XACK)

### Scaling

* Each agent type can run N instances
* Each instance is a consumer in the same group
* Pending messages auto-reassigned on failure

## 7. Failure Handling

* Crash during processing → PEL keeps unacknowledged tasks
* Timeouts → Agents claim PEL entries older than threshold
* Retries configurable per stream
* Partial results handled incrementally by aggregator

## 8. Extensibility

* Add new specialist agents (legal review, accessibility, multilingual)
* Coordinator fans out new streams automatically
* Minimal code changes required

## 9. Observability & Metrics

* Track per-stream: messages published, processed, pending
* Track per-agent: task latency, retries, failures
* Optional: Redis keyspace notifications or Prometheus exporters

## 10. Example Stream & Agent Naming Conventions

```
Streams:
  doc.review.tasks
  doc.review.grammar
  doc.review.clarity
  doc.review.tone
  doc.review.structure
  doc.suggestions.grammar
  doc.suggestions.clarity
  doc.suggestions.tone
  doc.suggestions.structure
  doc.review.summary

Consumer Groups:
  coordinator-group
  grammar-group
  clarity-group
  tone-group
  structure-group
  aggregator-group

Agents:
  coordinator-1..N
  grammar-1..N
  clarity-1..N
  tone-1..N
  structure-1..N
  aggregator-1..N
```

## 11. Optional Enhancements

* Dead-letter streams for failed chunks (doc.failed.*)
* Chunk prioritization
* Versioned suggestions for iterative editing
* Asynchronous UI updates

---

### Key Takeaways

1. Redis Streams = backbone for coordination + failure recovery
2. Coordinator agent = dynamic fan-out, modular system
3. Specialist agents = independent, horizontally scalable, replaceable
4. Aggregator = resolves conflicts and produces final user-facing output
5. Fully extendable for new AI review types or document formats
