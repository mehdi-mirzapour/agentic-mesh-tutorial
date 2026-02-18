import json
from .base import BaseAgent
from src.core.redis_client import (
    RedisClient, STREAM_DOC_TASKS, GROUP_COORDINATOR,
    STREAM_DOC_GRAMMAR, STREAM_DOC_CLARITY, STREAM_DOC_TONE, STREAM_DOC_STRUCTURE
)

class CoordinatorAgent(BaseAgent):
    def __init__(self, consumer_name="coordinator-1"):
        super().__init__(
            stream_name=STREAM_DOC_TASKS,
            consumer_group=GROUP_COORDINATOR,
            consumer_name=consumer_name
        )
        self.output_streams = {
            "grammar": STREAM_DOC_GRAMMAR,
            "clarity": STREAM_DOC_CLARITY,
            "tone": STREAM_DOC_TONE,
            "structure": STREAM_DOC_STRUCTURE
        }

    def process_message(self, message_id, data):
        """
        Receives a DocumentChunk.
        Fans out the task to different streams for processing.
        """
        # data is a dict like {"doc_id": "...", "text": "...", "chunk_id": "..."}
        # In Redis streams, data is stringified. If using json.dumps, ensure parsing.
        # But Redis XADD values are strings. We need to respect that.

        # Let's assume input data IS the payload.
        # Just fan out to all specialist streams
        
        doc_id = data.get("doc_id", "unknown")
        chunk_id = data.get("chunk_id", "unknown")
        
        print(f"[{self.consumer_name}] Fanning out task for doc {doc_id} chunk {chunk_id}")

        for task_type, stream_name in self.output_streams.items():
            # Add metadata for the specialist
            payload = data.copy()
            payload["task_type"] = task_type
            payload["parent_msg_id"] = message_id 
            
            # Write to specialist stream
            self.redis_client.xadd(stream_name, payload)
            print(f"[{self.consumer_name}] -> Pushed to {stream_name}")

if __name__ == "__main__":
    agent = CoordinatorAgent()
    agent.run()
