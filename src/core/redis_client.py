import redis
import os
import time
from typing import Optional, List, Any
from dotenv import load_dotenv

# Load env variables from .env file if present
load_dotenv()

# Load env variables (assume none for now or default localhost)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

class RedisClient:
    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_instance(cls) -> redis.Redis:
        if cls._instance is None:
            cls._instance = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True  # Important for string handling
            )
        return cls._instance

    @staticmethod
    def ensure_streams_exist(streams: List[str]):
        """Ensure streams exist (by adding a dummy message and deleting it if empty) 
           or just handle errors gracefully."""
        # Typically not needed if producers write first.
        pass

    @staticmethod
    def create_group(stream: str, group: str):
        r = RedisClient.get_instance()
        try:
            r.xgroup_create(stream, group, id="0", mkstream=True)
            print(f"Created consumer group '{group}' for stream '{stream}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                pass
            else:
                raise e

# Constants for Stream Names
STREAM_DOC_TASKS = "doc.review.tasks"
STREAM_DOC_GRAMMAR = "doc.review.grammar"
STREAM_DOC_CLARITY = "doc.review.clarity"
STREAM_DOC_TONE = "doc.review.tone"
STREAM_DOC_STRUCTURE = "doc.review.structure"

STREAM_SUGGESTIONS_GRAMMAR = "doc.suggestions.grammar"
STREAM_SUGGESTIONS_CLARITY = "doc.suggestions.clarity"
STREAM_SUGGESTIONS_TONE = "doc.suggestions.tone"
STREAM_SUGGESTIONS_STRUCTURE = "doc.suggestions.structure"

STREAM_REVIEW_SUMMARY = "doc.review.summary"

# Constants for Consumer Groups
GROUP_COORDINATOR = "coordinator-group"
GROUP_GRAMMAR = "grammar-group"
GROUP_CLARITY = "clarity-group"
GROUP_TONE = "tone-group"
GROUP_STRUCTURE = "structure-group"
GROUP_AGGREGATOR = "aggregator-group"
