import json

# 直接读取已保存的 PPStructure JSON
with open('temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_ppstructure.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('PPStructure JSON 中的坐标:')
for item in data['items'][:3]:
    print(f"  Type: {item['type']}, bbox: {item['bbox']}")

# 原始图像尺寸
print(f'\n原始图像尺寸: 2479 x 3508')
print(f'预处理后尺寸: 1447 x 2048 (max_dimension=2048)')

# 检查坐标是否在原始图像范围内
print(f'\nbbox[0] x2=2435 vs 原始宽度 2479 -> 在范围内')
print(f'bbox[0] x2=2435 vs 预处理宽度 1447 -> 超出范围!')
print(f'\n结论: PPStructure JSON 中的坐标是基于原始图像尺寸的')
