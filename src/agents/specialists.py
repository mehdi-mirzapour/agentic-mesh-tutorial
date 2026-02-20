import time
import json
import random
from datetime import datetime
from .base import BaseAgent
from src.core.redis_client import (
    RedisClient,
    STREAM_SUGGESTIONS_GRAMMAR,
    STREAM_SUGGESTIONS_CLARITY,
    STREAM_SUGGESTIONS_TONE,
    STREAM_SUGGESTIONS_STRUCTURE,
    GROUP_GRAMMAR,
    GROUP_CLARITY,
    GROUP_TONE,
    GROUP_STRUCTURE,
)

class SpecialistAgent(BaseAgent):
    def __init__(self, specialty: str, input_stream: str, output_stream: str, consumer_group: str, consumer_name: str):
        super().__init__(
            stream_name=input_stream,
            consumer_group=consumer_group,
            consumer_name=consumer_name
        )
        self.specialty = specialty
        self.output_stream = output_stream

    def process_message(self, message_id, data):
        """
        Simulate AI processing and return dummy suggestions.
        """
        doc_id = data.get("doc_id")
        chunk_id = data.get("chunk_id")
        text = data.get("text", "")
        
        print(f"[{self.consumer_name}] Analyzing chunk {chunk_id} for {self.specialty}...")
        
        # Simulate processing time
        time.sleep(random.uniform(0.5, 1.5))
        
        # Generate dummy suggestion
        suggestion = {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "original_text": text[:50] + "...",
            "suggested_text": f"{text}\n[AI SERVICE: {self.specialty.upper()} DONE]",
            "explanation": f"This is a dummy explanation from the {self.specialty} agent.",
            "source_agent": self.consumer_name,
            "type": self.specialty,
            "severity": random.choice(["low", "medium", "high"]),
            "timestamp": datetime.now().isoformat()
        }
        
        # Push to output stream
        # Redis streams are strings, so we dump JSON
        # Actually, let's keep it flat if possible, but nested JSON is easier to transport as a single field "data"
        # but standard redis pattern is field-value pairs.
        # I'll use standard field-value pairs for the top level keys.
        
        # Flatten for Redis
        redis_payload = {k: str(v) for k, v in suggestion.items()}
        
        self.redis_client.xadd(self.output_stream, redis_payload)
        print(f"[{self.consumer_name}] -> Suggestion posted to {self.output_stream}")

# Factory functions to create specific agents
def create_grammar_agent(name_suffix="1"):
    return SpecialistAgent(
        specialty="grammar",
        input_stream="doc.review.grammar",
        output_stream=STREAM_SUGGESTIONS_GRAMMAR,
        consumer_group=GROUP_GRAMMAR,
        consumer_name=f"grammar-{name_suffix}"
    )

def create_clarity_agent(name_suffix="1"):
    return SpecialistAgent(
        specialty="clarity",
        input_stream="doc.review.clarity",
        output_stream=STREAM_SUGGESTIONS_CLARITY,
        consumer_group=GROUP_CLARITY,
        consumer_name=f"clarity-{name_suffix}"
    )

def create_tone_agent(name_suffix="1"):
    return SpecialistAgent(
        specialty="tone",
        input_stream="doc.review.tone",
        output_stream=STREAM_SUGGESTIONS_TONE,
        consumer_group=GROUP_TONE,
        consumer_name=f"tone-{name_suffix}"
    )

def create_structure_agent(name_suffix="1"):
    return SpecialistAgent(
        specialty="structure",
        input_stream="doc.review.structure",
        output_stream=STREAM_SUGGESTIONS_STRUCTURE,
        consumer_group=GROUP_STRUCTURE,
        consumer_name=f"structure-{name_suffix}"
    )
