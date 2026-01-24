import requests
import json

# 测试 API 返回的 confidence 数据
r = requests.get('http://localhost:5000/api/convert/8a7e1ef0-1842-49df-8b30-879efb28527f/result')
data = r.json()
blocks = data.get('result', {}).get('blocks', [])

print(f'Total blocks: {len(blocks)}')
print()

for i, b in enumerate(blocks[:10]):
    block_type = b.get('type')
    metadata = b.get('metadata', {})
    confidence = metadata.get('confidence')
    print(f'Block {i}: type={block_type}, metadata.confidence={confidence}')
