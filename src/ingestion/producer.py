import time
import shortuuid
import click
from src.core.redis_client import RedisClient, STREAM_DOC_TASKS

def run_producer(doc_id, paragraphs):
    r = RedisClient.get_instance()
    
    print(f"Uploading document {doc_id} with {paragraphs} chunks...")
    
    sample_texts = [
        "The quick brown fox jumps over the lazy dog. But is it grammatically correct? We shall see.",
        "To define the recursive loop is to understand the loop itself, which is redundant and confusing.",
        "Hey wuts up, this is a very informal text that needs tone correction ASAP!!!",
        "Structure of this document is non-existent. Headers are missing. Chaos reigns."
    ]
    
    for i in range(paragraphs):
        chunk_id = f"p-{shortuuid.uuid()}"
        text = sample_texts[i % len(sample_texts)]
        
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
@click.option("--paragraphs", default=3, help="Number of paragraphs to simulate")
def produce_document(doc_id, paragraphs):
    run_producer(doc_id, paragraphs)

if __name__ == "__main__":
    produce_document()
