# Manual Redis Architecture Simulation

This guide explains how to manually simulate the entire `agentic-mesh` architecture using only `redis-cli`. This is useful for debugging, understanding the message flow, and testing individual components in isolation.

## Prerequisites

- Redis server running (locally or in Docker).
- `redis-cli` installed and connected.
- If using Docker: `docker exec -it redis-mesh redis-cli`

---

## Architecture Flow Overview

1.  **Ingestion/Producer**: Pushes raw document chunks to `doc.review.tasks`.
2.  **Coordinator Agent**: Reads from `doc.review.tasks` and fans out to `doc.review.<specialty>`.
3.  **Specialist Agents**: Read from `doc.review.<specialty>` and push suggestions to `doc.suggestions.<specialty>`.
4.  **Aggregator Agent**: Reads from all `doc.suggestions.*` and summarizes in `doc.review.summary`.

---

## 1. Setup Consumer Groups

Before starting, ensure the consumer groups exist. Run these commands once:

```bash
# Coordinator Group
XGROUP CREATE doc.review.tasks coordinator-group 0 MKSTREAM

# Specialist Groups
XGROUP CREATE doc.review.grammar grammar-group 0 MKSTREAM
XGROUP CREATE doc.review.clarity clarity-group 0 MKSTREAM
XGROUP CREATE doc.review.tone tone-group 0 MKSTREAM
XGROUP CREATE doc.review.structure structure-group 0 MKSTREAM

# Aggregator Group
XGROUP CREATE doc.suggestions.grammar aggregator-group 0 MKSTREAM
XGROUP CREATE doc.suggestions.clarity aggregator-group 0 MKSTREAM
XGROUP CREATE doc.suggestions.tone aggregator-group 0 MKSTREAM
XGROUP CREATE doc.suggestions.structure aggregator-group 0 MKSTREAM
```

---

## 2. Step-by-Step Simulation

### Step A: Act as the Producer
Add a document chunk to the system.

```bash
XADD doc.review.tasks * doc_id "manual-doc-001" chunk_id "c1" text "This is some text with grammer errors and bad tone."
```
*Note the returned Message ID (e.g., `1676543210123-0`).*

### Step B: Act as the Coordinator
Read the task and fan it out to specialists.

1.  **Read from task stream:**
    ```bash
    XREADGROUP GROUP coordinator-group manual-coord COUNT 1 STREAMS doc.review.tasks >
    ```
2.  **Fan out (Manual Step):**
    For each specialist, add the message to their specific stream:
    ```bash
    XADD doc.review.grammar * doc_id "manual-doc-001" chunk_id "c1" text "..." task_type "grammar"
    XADD doc.review.clarity * doc_id "manual-doc-001" chunk_id "c1" text "..." task_type "clarity"
    ```
3.  **ACK the original task:**
    ```bash
    XACK doc.review.tasks coordinator-group <MESSAGE_ID_FROM_STEP_1>
    ```

### Step C: Act as a Specialist (e.g., Grammar Agent)
Process the specific task and provide a suggestion.

1.  **Read the review task:**
    ```bash
    XREADGROUP GROUP grammar-group manual-grammar-1 COUNT 1 STREAMS doc.review.grammar >
    ```
2.  **Post a suggestion:**
    ```bash
    XADD doc.suggestions.grammar * doc_id "manual-doc-001" chunk_id "c1" suggested_text "This is some text with grammar errors and professional tone." source_agent "manual-grammar-1" type "grammar"
    ```
3.  **ACK the task:**
    ```bash
    XACK doc.review.grammar grammar-group <MESSAGE_ID_FROM_STEP_1>
    ```

### Step D: Act as the Aggregator
Collect suggestions and post a final summary.

1.  **Read from suggestion streams:**
    ```bash
    XREADGROUP GROUP aggregator-group manual-agg-1 COUNT 1 STREAMS doc.suggestions.grammar >
    ```
2.  **Post to summary stream:**
    ```bash
    XADD doc.review.summary * type "final_suggestion" original_stream "doc.suggestions.grammar" data '{"doc_id": "manual-doc-001", "suggestion": "..."}'
    ```
3.  **ACK the suggestion:**
    ```bash
    XACK doc.suggestions.grammar aggregator-group <MESSAGE_ID_FROM_STEP_1>
    ```

---

## 3. Useful Inspection Commands

| Action | Command |
| :--- | :--- |
| **List all streams** | `SCAN 0 TYPE stream` |
| **Check stream length** | `XLEN doc.review.tasks` |
| **View recent messages** | `XREVRANGE doc.review.tasks + - COUNT 5` |
| **Check group status** | `XINFO GROUPS doc.review.tasks` |
| **Check pending messages** | `XPENDING doc.review.tasks coordinator-group` |
| **Delete a stream** | `DEL doc.review.tasks` |

---

## 4. Troubleshooting

- **No messages returned?** Make sure you use `>` in `XREADGROUP` to get only new messages.
- **Message already read?** If you need to re-read messages that weren't ACKed, replace `>` with `0`.
- **Stream doesn't exist?** `XADD` automatically creates the stream unless told otherwise, but `XGROUP CREATE` with `MKSTREAM` is safer.
