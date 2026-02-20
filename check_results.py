import json
from src.core.redis_client import RedisClient

r = RedisClient.get_instance()
messages = r.xrevrange("doc.review.summary", count=5)

for msg_id, data in messages:
    print(f"ID: {msg_id}")
    raw_data = data.get('data')
    if raw_data:
        inner_data = json.loads(raw_data)
        print(f"  Source: {inner_data.get('source_agent')}")
        print(f"  Suggested: {inner_data.get('suggested_text')}")
    else:
        print(f"  Raw: {data}")
    print("-" * 20)
