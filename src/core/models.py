from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import shortuuid
import time

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentChunk(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    language: str = "en"
    style: str = "standard"
    created_at: float = Field(default_factory=time.time)

class SuggestionType(str, Enum):
    GRAMMAR = "grammar"
    CLARITY = "clarity"
    TONE = "tone"
    STRUCTURE = "structure"

class Suggestion(BaseModel):
    doc_id: str
    chunk_id: str
    suggestion_id: str = Field(default_factory=lambda: shortuuid.uuid())
    type: SuggestionType
    original_text: str
    suggested_text: str
    explanation: str
    severity: str = "medium"  # low, medium, high
    source_agent: str
    created_at: float = Field(default_factory=time.time)

class ReviewSummary(BaseModel):
    doc_id: str
    total_chunks: int
    processed_chunks: int
    suggestions: List[Suggestion] = []
    status: ProcessingStatus = ProcessingStatus.PROCESSING
    updated_at: float = Field(default_factory=time.time)
