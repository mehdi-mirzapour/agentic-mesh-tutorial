# Redis CLI Manual Flow Diagram

This diagram visualizes the interactive manual process for simulating the agentic mesh via CLI.

```mermaid
graph TD
    %% Node Definitions with simple alphanumeric IDs
    producer_cli["Step A: Act as Producer"]
    coord_cli["Step B: Act as Coordinator"]
    specialist_cli["Step C: Act as Specialist"]
    aggregator_cli["Step D: Act as Aggregator"]

    %% Stream Definitions
    stream_tasks[("doc.review.tasks")]
    stream_review[("doc.review.*")]
    stream_suggestions[("doc.suggestions.*")]
    stream_summary[("doc.review.summary")]

    %% Interactions
    producer_cli -->|"1. XADD (Add Chunk)"| stream_tasks
    
    stream_tasks -.->|"2. XREADGROUP (Read Task)"| coord_cli
    coord_cli -->|"3. XADD (Fan Out)"| stream_review
    coord_cli -.->|"4. XACK (Confirm Task)"| stream_tasks

    stream_review -.->|"5. XREADGROUP (Work)"| specialist_cli
    specialist_cli -->|"6. XADD (Suggestion)"| stream_suggestions
    specialist_cli -.->|"7. XACK (Confirm Review)"| stream_review

    stream_suggestions -.->|"8. XREADGROUP (Collect)"| aggregator_cli
    aggregator_cli -->|"9. XADD (Finalize)"| stream_summary
    aggregator_cli -.->|"10. XACK (Confirm Result)"| stream_suggestions

    %% Styling for Premium Look
    classDef step fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#01579b,font-weight:bold;
    classDef stream fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100;
    classDef final fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;

    class producer_cli,coord_cli,specialist_cli,aggregator_cli step;
    class stream_tasks,stream_review,stream_suggestions stream;
    class stream_summary final;
```

## Description of Interactions

- **Solid Lines**: `XADD` commands that push data forward into the next stage.
- **Dashed Lines**: `XREADGROUP` and `XACK` commands that manage the lifecycle of a message within a consumer group.
