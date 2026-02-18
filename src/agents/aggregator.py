import time
import json
import redis
from .base import BaseAgent
from src.core.redis_client import (
    RedisClient,
    STREAM_SUGGESTIONS_GRAMMAR,
    STREAM_SUGGESTIONS_CLARITY,
    STREAM_SUGGESTIONS_TONE,
    STREAM_SUGGESTIONS_STRUCTURE,
    STREAM_REVIEW_SUMMARY,
    GROUP_AGGREGATOR
)

class AggregatorAgent(BaseAgent):
    def __init__(self, consumer_name="aggregator-1"):
        # We don't use the single stream init of BaseAgent fully, but we call super to get redis client
        # Pass dummy stream/group to super to avoid errors? No, BaseAgent init does creating group.
        # We'll just init with one stream, and then add the others.
        super().__init__(
            stream_name=STREAM_SUGGESTIONS_GRAMMAR, 
            consumer_group=GROUP_AGGREGATOR, 
            consumer_name=consumer_name
        )
        
        self.input_streams = [
            STREAM_SUGGESTIONS_GRAMMAR,
            STREAM_SUGGESTIONS_CLARITY,
            STREAM_SUGGESTIONS_TONE,
            STREAM_SUGGESTIONS_STRUCTURE
        ]
        
        # Ensure groups exist for all input streams
        for stream in self.input_streams:
            if stream == STREAM_SUGGESTIONS_GRAMMAR: continue # Already done by super
            try:
                self.redis_client.xgroup_create(stream, self.consumer_group, id="0", mkstream=True)
                print(f"[{self.consumer_name}] Created consumer group '{self.consumer_group}' on '{stream}'")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    pass
                else:
                    raise e
                    
    def run(self):
        print(f"[{self.consumer_name}] Aggregator Starting up... Listening on {self.input_streams}")
        
        streams_dict = {stream: ">" for stream in self.input_streams}

        while self.should_run:
            try:
                messages = self.redis_client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams=streams_dict,
                    count=10,
                    block=2000,
                )

                if messages:
                    for stream, msgs in messages:
                        for message_id, data in msgs:
                            print(f"[{self.consumer_name}] Received suggestion from {stream} (ID: {message_id})")
                            
                            try:
                                self.process_message(message_id, data, stream)
                                self.redis_client.xack(stream, self.consumer_group, message_id)
                            except Exception as e:
                                print(f"[{self.consumer_name}] Error processing {message_id}: {e}")
                                continue
            except Exception as e:
                print(f"[{self.consumer_name}] Critical error: {e}")
                time.sleep(1)

    def process_message(self, message_id, data, source_stream):
        """
        Aggregate suggestions.
        For now, we just format them and push to the final summary stream.
        """
        doc_id = data.get("doc_id", "unknown")
        # In a real system, we might buffer these by doc_id and release a batch.
        # Here, we stream them to the final output immediately.
        
        summary_payload = {
            "type": "final_suggestion",
            "original_stream": source_stream,
            "data": json.dumps(data) if not isinstance(data, str) else data,
            "processed_at": time.time()
        }
        
        self.redis_client.xadd(STREAM_REVIEW_SUMMARY, summary_payload)
        print(f"[{self.consumer_name}] -> Pushed to {STREAM_REVIEW_SUMMARY}")
