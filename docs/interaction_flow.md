# System Interaction Flow

This document details the interaction sequences and data flow states of the Word Document Suggestion Mesh.

## 1. Sequence Diagram: Document Processing Lifecycle

This diagram shows the step-by-step interaction between components over time, from upload to final suggestion delivery.

```mermaid
sequenceDiagram
    autonumber
    participant U as User / Word Add-in
    participant I as Ingestion Service
    participant R as Redis Streams
    participant C as Coordinator Agent
    participant G as Grammar Agent
    participant T as Tone Agent
    participant A as Aggregator Agent

    %% Upload Phase
    rect rgb(240, 248, 255)
    note right of U: Input Phase
    U->>I: Upload .docx File
    activate I
    I->>I: Parse .docx structure
    I->>I: Split into Chunks (C1, C2...)
    I->>R: XADD doc.review.tasks (Chunk Data)
    deactivate I
    end

    %% Coordination Phase
    rect rgb(255, 250, 205)
    note right of R: Coordination
    R-->>C: New Message (Chunk Data)
    activate C
    C->>C: Analyze Request
    par Fan Out Tasks
        C->>R: XADD doc.review.grammar
        C->>R: XADD doc.review.tone
    end
    C->>R: XACK doc.review.tasks
    deactivate C
    end

    %% Specialist Processing Phase
    rect rgb(255, 228, 225)
    note right of R: Specialist Processing
    par Parallel Processing
        R-->>G: Read doc.review.grammar
        activate G
        G->>G: Check Grammar Rules
        G->>R: XADD doc.suggestions.grammar
        G->>R: XACK doc.review.grammar
        deactivate G
    and
        R-->>T: Read doc.review.tone
        activate T
        T->>T: Check Tone Consistency
        T->>R: XADD doc.suggestions.tone
        T->>R: XACK doc.review.tone
        deactivate T
    end
    end

    %% Aggregation & Delivery
    rect rgb(240, 255, 240)
    note right of A: Aggregation & Output
    loop Collecting Results
        R-->>A: Read doc.suggestions.*
        activate A
        A->>A: Buffer & Group by DocID
    end
    
    A->>A: Merge Suggestions
    A->>R: XADD doc.review.summary
    deactivate A

    R-->>U: Read Final Summary
    U->>U: Display Suggestions
    end
```

## 2. Interaction Explanation

### Phase 1: Input
The **User** uploads a file. The **Ingestion Service** acts as the boundary, converting the binary `.docx` file into discrete, text-based tasks stored in **Redis**. This decouples the upload speed from the processing speed.

### Phase 2: Coordination
The **Coordinator Agent** picks up the raw text chunk. It decides *what* needs to be done. If the user only requested a grammar check, it would only publish to `doc.review.grammar`. In this diagram, it fans out to both **Grammar** and **Tone** streams.

### Phase 3: Specialist Processing
The **Grammar** and **Tone agents** work in parallel. They are completely unaware of each other ("shared nothing architecture"). They read their specific tasks, perform CPU-heavy AI processing, and write their findings to a common `doc.suggestions.*` pattern.

### Phase 4: Aggregation
The **Aggregator** listens to *all* suggestion channels. It waits until it has received feedback from all expected agents for a specific chunk (or hits a timeout). It then merges these separate JSON objects into a single, cohesive result and publishes it to the summary stream for the **User** to consume.
