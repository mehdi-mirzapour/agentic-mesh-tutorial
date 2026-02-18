---
name: Create New Agent
description: Instructions for creating a new specialist or coordinator agent within the Agentic Mesh architecture.
---

# Create New Agent

This skill guides you through creating a new agent in the `agentic-mesh` system. All agents invoke `BaseAgent` and interact via Redis Streams.

## 1. Define Constants
First, define the necessary stream and consumer group constants in `src/core/redis_client.py`.

```python
# src/core/redis_client.py

# ... existing streams ...
STREAM_NEW_SPECIALTY = "doc.review.new_specialty"
STREAM_SUGGESTIONS_NEW_SPECIALTY_RESULT = "doc.suggestions.new_specialty"

# ... existing groups ...
GROUP_NEW_SPECIALTY = "new-specialty-group"
```

## 2. Create Agent Class
Create a new class in `src/agents/` (or add to `specialists.py` if it fits there) that inherits from `BaseAgent`.

```python
from src.agents.base import BaseAgent
from src.core.redis_client import RedisClient

class NewSpecialtyAgent(BaseAgent):
    def __init__(self, input_stream: str, output_stream: str, consumer_group: str, consumer_name: str):
        super().__init__(
            stream_name=input_stream,
            consumer_group=consumer_group,
            consumer_name=consumer_name
        )
        self.output_stream = output_stream

    def process_message(self, message_id, data):
        """
        Process the incoming message logic here.
        """
        print(f"[{self.consumer_name}] Processing {message_id}...")
        
        # extracted data
        # content = data.get("content")
        
        # Result logic...
        result = {
            "processed": True,
            "original_id": message_id
        }
        
        # Publish result if necessary
        if self.output_stream:
             self.redis_client.xadd(self.output_stream, result)
             print(f"[{self.consumer_name}] Published result to {self.output_stream}")
```

## 3. Create Factory Function
Add a factory function to easily instantiate the agent with default configuration.

```python
def create_new_specialty_agent(name_suffix="1"):
    return NewSpecialtyAgent(
        input_stream=STREAM_NEW_SPECIALTY,
        output_stream=STREAM_SUGGESTIONS_NEW_SPECIALTY_RESULT,
        consumer_group=GROUP_NEW_SPECIALTY,
        consumer_name=f"new-specialty-{name_suffix}"
    )
```

## 4. Register in Main
Update `src/main.py` (or the relevant runner script) to start this agent.

```python
# src/main.py
from src.agents.new_specialty import create_new_specialty_agent
import threading

def start_new_agent():
    agent = create_new_specialty_agent()
    agent.run()

# ... inside main execution block ...
t = threading.Thread(target=start_new_agent, daemon=True)
t.start()
```

## Best Practices
- **Idempotency**: Ensure `process_message` can handle the same message ID multiple times without side effects if possible (though Redis guarantees exactly-once delivery within a group if ACKed correctly, crashes before ACK can cause redelivery).
- **Error Handling**: `BaseAgent` catches exceptions in the loop, but your `process_message` should handle specific logic errors gracefully.
- **Data Types**: Redis Streams store strings. Complex objects must be serialized (JSON) or stored as flat key-value pairs.
