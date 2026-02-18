# Redis Stream Architecture

This diagram details the specific Redis Streams and Consumer Groups implementation in the system.

## Redis Implementation Diagram

```mermaid
graph TD
    %% Nodes representing Redis Clients / Agents
    producer[Producer Script]
    coord[Coordinator Agent]
    
    subgraph specialists [Specialist Agents]
        grammar[Grammar Agent]
        clarity[Clarity Agent]
        tone[Tone Agent]
        struct[Structure Agent]
    end
    
    agg[Aggregator Agent]

    %% Redis Streams represented as cylinders
    subgraph redis [Redis Streams]
        s_tasks[Stream: doc.review.tasks]
        s_gram[Stream: doc.review.grammar]
        s_clar[Stream: doc.review.clarity]
        s_tone[Stream: doc.review.tone]
        s_struct[Stream: doc.review.structure]
        
        s_sugg_gram[Stream: doc.suggestions.grammar]
        s_sugg_clar[Stream: doc.suggestions.clarity]
        s_sugg_tone[Stream: doc.suggestions.tone]
        s_sugg_struct[Stream: doc.suggestions.structure]
        
        s_summary[Stream: doc.review.summary]
    end

    %% Flows
    producer -->|XADD| s_tasks
    
    %% Coordinator Reading
    s_tasks -->|XREADGROUP: coordinator-group| coord
    
    %% Coordinator Fan-out
    coord -->|XADD| s_gram
    coord -->|XADD| s_clar
    coord -->|XADD| s_tone
    coord -->|XADD| s_struct
    
    %% Specialists Reading
    s_gram -->|XREADGROUP: grammar-group| grammar
    s_clar -->|XREADGROUP: clarity-group| clarity
    s_tone -->|XREADGROUP: tone-group| tone
    s_struct -->|XREADGROUP: structure-group| struct
    
    %% Specialists Writing
    grammar -->|XADD| s_sugg_gram
    clarity -->|XADD| s_sugg_clar
    tone -->|XADD| s_sugg_tone
    struct -->|XADD| s_sugg_struct
    
    %% Aggregator Reading
    s_sugg_gram -->|XREADGROUP: aggregator-group| agg
    s_sugg_clar -->|XREADGROUP: aggregator-group| agg
    s_sugg_tone -->|XREADGROUP: aggregator-group| agg
    s_sugg_struct -->|XREADGROUP: aggregator-group| agg
    
    %% Final Summary
    agg -->|XADD| s_summary
```

## Key Redis Commands Used

| Action | Command | Python Implementation |
| :--- | :--- | :--- |
| **Publishing Tasks** | `XADD key * field value` | `redis_client.xadd(stream, payload)` |
| **Consuming Tasks** | `XREADGROUP GROUP group consumer STREAMS key >` | `redis_client.xreadgroup(...)` |
| **Acknowledge** | `XACK key group id` | `redis_client.xack(...)` |
| **Create Group** | `XGROUP CREATE key group $ MKSTREAM` | `redis_client.xgroup_create(...)` |
