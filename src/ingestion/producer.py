from docx import Document
import time
import shortuuid
import click
import os
from src.core.redis_client import RedisClient, STREAM_DOC_TASKS

def run_producer(doc_id, paragraphs=None, file_path=None):
    r = RedisClient.get_instance()
    
    texts = []
    if file_path and os.path.exists(file_path):
        print(f"Reading from file: {file_path}")
        doc = Document(file_path)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
    else:
        print(f"Uploading document {doc_id} with {paragraphs} simulated chunks...")
        sample_texts = [
            "The quick brown fox jumps over the lazy dog. But is it grammatically correct? We shall see.",
            "To define the recursive loop is to understand the loop itself, which is redundant and confusing.",
            "Hey wuts up, this is a very informal text that needs tone correction ASAP!!!",
            "Structure of this document is non-existent. Headers are missing. Chaos reigns."
        ]
        num_to_gen = paragraphs if paragraphs else 3
        texts = [sample_texts[i % len(sample_texts)] for i in range(num_to_gen)]
    
    for i, text in enumerate(texts):
        chunk_id = f"p-{shortuuid.uuid()}"
        
        payload = {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "text": text,
            "language": "en",
            "timestamp": time.time()
        }
        
        msg_id = r.xadd(STREAM_DOC_TASKS, payload)
        print(f"[Producer] sent chunk {chunk_id} -> {msg_id}")
        time.sleep(0.5)

    print("Document upload complete.")

@click.command()
@click.option("--doc_id", default="doc-test-1", help="Document ID")
@click.option("--paragraphs", default=None, type=int, help="Number of paragraphs to simulate (if no file)")
@click.option("--file", default=None, help="Path to .docx file")
def produce_document(doc_id, paragraphs, file):
    run_producer(doc_id, paragraphs, file)

if __name__ == "__main__":
    produce_document()
