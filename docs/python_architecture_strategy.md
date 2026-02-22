# Python Architecture Strategy: Independent Producers & Consumers

This document maps every step in `redis_cli_manual.md` to its Python implementation. The core rule is simple:

> **Every `XADD` is a produce. Every `XREADGROUP` + `XACK` pair is a consume.**

Each agent is a self-contained, independent process that knows only its own input stream and its own output stream. No agent talks to another agent directly — they only communicate through Redis streams.

---

## Step A → `src/ingestion/producer.py` (Pure Producer)

The producer fires document chunks into the system and exits. It does not listen on any stream.

```bash
# redis-cli equivalent:
XADD doc.review.tasks * doc_id "manual-doc-001" chunk_id "c1" text "..."
```

```python
# Python: src/ingestion/producer.py
r.xadd("doc.review.tasks", {
    "doc_id":    doc_id,
    "chunk_id":  chunk_id,
    "text":      text,
    "timestamp": time.time(),
})
```

**Role:** Pure Producer — writes to `doc.review.tasks` only. Terminates after all chunks are sent.

---

## Step B → `src/agents/coordinator.py` (Consumer + Fan-out Producer)

The coordinator reads one task at a time and replicates it to every specialist stream. It acts as a router.

```bash
# redis-cli equivalent:
XREADGROUP GROUP coordinator-group coord-1 COUNT 1 STREAMS doc.review.tasks >
XADD doc.review.grammar * doc_id "..." chunk_id "..." text "..." task_type "grammar"
XADD doc.review.clarity * doc_id "..." chunk_id "..." text "..." task_type "clarity"
XADD doc.review.tone    * doc_id "..." chunk_id "..." text "..." task_type "tone"
XADD doc.review.structure * doc_id "..." chunk_id "..." text "..." task_type "structure"
XACK doc.review.tasks coordinator-group <MESSAGE_ID>
```

```python
# Python: src/agents/coordinator.py
messages = r.xreadgroup(
    groupname="coordinator-group",
    consumername="coord-1",
    streams={"doc.review.tasks": ">"},  # ">" means: only new, undelivered messages
    count=10,
    block=2000,
)

for _, msgs in messages:
    for msg_id, data in msgs:
        # Fan-out to all specialist streams
        for task_type, stream in self.output_streams.items():
            payload = {**data, "task_type": task_type}
            r.xadd(stream, payload)

        # ACK the original task
        r.xack("doc.review.tasks", "coordinator-group", msg_id)
```

**Role:** Consumer of `doc.review.tasks` + Producer to four specialist streams.

---

## Step C → `src/agents/specialists.py` (Independent Consumer + Producer, ×4)

Each specialist is a completely separate process. They share the same code structure (`SpecialistAgent` class) but run independently with different stream names. In deployment, each is its own container.

```bash
# redis-cli equivalent (grammar agent):
XREADGROUP GROUP grammar-group grammar-1 COUNT 1 STREAMS doc.review.grammar >
XADD doc.suggestions.grammar * doc_id "..." suggested_text "..." type "grammar"
XACK doc.review.grammar grammar-group <MESSAGE_ID>
```

```python
# Python: src/agents/specialists.py (all four agents share this pattern)
class SpecialistAgent(BaseAgent):
    def __init__(self, specialty, input_stream, output_stream, consumer_group, consumer_name):
        self.specialty     = specialty
        self.input_stream  = input_stream
        self.output_stream = output_stream
        # BaseAgent.run() handles the XREADGROUP + XACK loop automatically

    def process_message(self, message_id, data):
        suggestion = {
            "doc_id":         data["doc_id"],
            "chunk_id":       data["chunk_id"],
            "suggested_text": f"{data['text']}\n[AI: {self.specialty.upper()} DONE]",
            "source_agent":   self.consumer_name,
            "type":           self.specialty,
        }
        # Produce to own output stream
        r.xadd(self.output_stream, suggestion)


# Four independent agent factories — each is a separate deployed process:
grammar_agent   = SpecialistAgent("grammar",   "doc.review.grammar",   "doc.suggestions.grammar",   ...)
clarity_agent   = SpecialistAgent("clarity",   "doc.review.clarity",   "doc.suggestions.clarity",   ...)
tone_agent      = SpecialistAgent("tone",      "doc.review.tone",      "doc.suggestions.tone",      ...)
structure_agent = SpecialistAgent("structure", "doc.review.structure", "doc.suggestions.structure", ...)
```

**Role:** Each is an independent Consumer of its review stream + Producer to its suggestions stream.

---

## Step D → `src/agents/aggregator.py` (Multi-stream Consumer + Final Producer)

The aggregator listens on all four suggestion streams simultaneously and writes a final summary.

```bash
# redis-cli equivalent:
XREADGROUP GROUP aggregator-group agg-1 COUNT 10 STREAMS \
  doc.suggestions.grammar   > \
  doc.suggestions.clarity   > \
  doc.suggestions.tone      > \
  doc.suggestions.structure >
XADD doc.review.summary * type "final_suggestion" original_stream "..." data "..."
XACK doc.suggestions.grammar aggregator-group <MESSAGE_ID>
```

```python
# Python: src/agents/aggregator.py
input_streams = {
    "doc.suggestions.grammar":   ">",
    "doc.suggestions.clarity":   ">",
    "doc.suggestions.tone":      ">",
    "doc.suggestions.structure": ">",
}

messages = r.xreadgroup(
    groupname="aggregator-group",
    consumername="agg-1",
    streams=input_streams,
    count=10,
    block=2000,
)

for source_stream, msgs in messages:
    for msg_id, data in msgs:
        r.xadd("doc.review.summary", {
            "type":            "final_suggestion",
            "original_stream": source_stream,
            "data":            json.dumps(data),
            "processed_at":    time.time(),
        })
        r.xack(source_stream, "aggregator-group", msg_id)
```

**Role:** Multi-stream Consumer of all suggestion streams + Producer to `doc.review.summary`.

---

## The `BaseAgent` Contract

All consuming agents inherit from `BaseAgent`, which provides the standard loop:

```python
class BaseAgent(ABC):
    def run(self):
        while self.should_run:
            messages = r.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.stream_name: ">"},
                count=10,
                block=2000,
            )
            for _, msgs in messages:
                for msg_id, data in msgs:
                    self.process_message(msg_id, data)  # <- subclass implements this
                    r.xack(self.stream_name, self.consumer_group, msg_id)

    @abstractmethod
    def process_message(self, message_id, data):
        pass  # Coordinator, Specialist, Aggregator each override this
```

The `process_message` method is the only thing each agent needs to implement. The reading, blocking, and ACKing is shared infrastructure.

---

## Summary Table

| Manual Step | Python File | Role | Input Stream | Output Stream |
|---|---|---|---|---|
| Step A | `ingestion/producer.py` | **Pure Producer** | — | `doc.review.tasks` |
| Step B | `agents/coordinator.py` | **Consumer + Fan-out Producer** | `doc.review.tasks` | `doc.review.*` (×4) |
| Step C | `agents/specialists.py` | **4× Independent Consumer + Producer** | `doc.review.<type>` | `doc.suggestions.<type>` |
| Step D | `agents/aggregator.py` | **Multi-Consumer + Final Producer** | `doc.suggestions.*` (×4) | `doc.review.summary` |

---

## Key Design Principles

1. **No direct agent-to-agent communication.** All messaging goes through Redis streams.
2. **`BaseAgent` provides the standard XREADGROUP + XACK loop.** Subclasses only define `process_message`.
3. **Consumer Groups provide load balancing.** Scale any specialist by deploying more instances with the same group name — Redis distributes the messages automatically.
4. **`>` means new messages only.** Using `0` instead would replay all pending (unACKed) messages — useful for crash recovery.
5. **ACK only after successful processing.** If the agent crashes before `XACK`, the message stays in the Pending Entry List (PEL) and will be redelivered.
