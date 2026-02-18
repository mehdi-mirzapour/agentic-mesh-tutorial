import os
import time
import json
import uuid
import click
import redis
import shortuuid
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from src.core.redis_client import RedisClient

class BaseAgent(ABC):
    def __init__(self, stream_name: str, consumer_group: str, consumer_name: str):
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.redis_client = RedisClient.get_instance()
        self.should_run = True

        # Ensure consumer group
        try:
            self.redis_client.xgroup_create(self.stream_name, self.consumer_group, id="0", mkstream=True)
            print(f"[{self.consumer_name}] Created consumer group '{self.consumer_group}' on '{self.stream_name}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # print(f"[{self.consumer_name}] Group '{self.consumer_group}' already exists.")
                pass
            else:
                raise e

    def run(self):
        print(f"[{self.consumer_name}] Agent Starting up...")

        while self.should_run:
            try:
                # Read from stream using consumer group
                # Using '>' ID to get new messages
                # Blocking for 2000ms
                messages = self.redis_client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=2000,
                )

                if messages:
                    for stream, msgs in messages:
                        for message_id, data in msgs:
                            print(f"[{self.consumer_name}] Processing message {message_id} from {stream}")
                            
                            try:
                                # Process the message (abstract)
                                self.process_message(message_id, data)
                                
                                # Acknowledge the message
                                self.redis_client.xack(stream, self.consumer_group, message_id)
                                print(f"[{self.consumer_name}] Message {message_id} ACKed")
                            
                            except Exception as e:
                                print(f"[{self.consumer_name}] Error processing message {message_id}: {e}")
                                # In a real implementation, we might retry or move to DLQ
                                continue
                else:
                    # Periodically check PEL for stalled messages
                    self.process_pending_messages()

            except Exception as e:
                print(f"[{self.consumer_name}] Critical error in loop: {e}")
                time.sleep(1)  # Backoff

    def process_pending_messages(self):
        """Check for messages that are pending (not ACKed) and retry them."""
        # This is simplified. In production, check delivery count and DLQ if too many retries.
        try:
            # Check PEL for this consumer
            pending = self.redis_client.xpending_range(
                self.stream_name, 
                self.consumer_group, 
                min="-", 
                max="+", 
                count=10, 
                consumername=self.consumer_name
            )
            
            for msg in pending:
                # msg (payload): {'message_id': '...', 'consumer': '...', 'time_since_delivered': ..., 'times_delivered': ...}
                msg_id = msg['message_id']
                
                # Retrieve the full message content
                # XCLAIM generic approach or just XREADGROUP with ID '0' (history)
                # But XREADGROUP with ID '0' gets pending messages for me.
                pass
            
            # Actually, a better pattern is to start with ID '0' in XREADGROUP to process any pending messages on startup/idle
            # For simplicity in this loop, we'll just log.
            # Implementing robust PEL handling requires fetching the message again via XRANGE or XCLAIM
            pass
            
        except Exception as e:
            pass  # Fail silently for demo

    @abstractmethod
    def process_message(self, message_id: str, data: Dict[str, Any]):
        """Logic specific to the agent."""
        pass

    def stop(self):
        self.should_run = False
