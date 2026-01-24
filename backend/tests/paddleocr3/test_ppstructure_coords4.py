"""
测试 PPStructureV3 返回的坐标是基于什么尺寸
"""
from paddleocr import PPStructureV3
from PIL import Image

# 原始图像
img_path = 'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png'
img = Image.open(img_path)
print(f'原始图像尺寸: {img.size}')

# 用 PPStructureV3 处理原始图像
print('\n正在加载 PPStructureV3...')
ppstructure = PPStructureV3()

print('\n处理原始图像...')
results = list(ppstructure.predict(
    img_path,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False
))

print('\nPPStructureV3 返回的结果:')
for result in results:
    print(f'Result width: {result["width"]}')
    print(f'Result height: {result["height"]}')
    
    # 检查 parsing_res_list
    parsing_res = result.get('parsing_res_list', [])
    print(f'\nparsing_res_list: {len(parsing_res)} items')
    
    for i, block in enumerate(parsing_res[:5]):
        print(f'\n  Block {i}:')
        print(f'    label: {block.label}')
        print(f'    bbox: {block.bbox}')
        # 检查坐标是否在图像范围内
        bbox = block.bbox
        if bbox[2] > result["width"]:
            print(f'    WARNING: x2={bbox[2]} > width={result["width"]}')
        if bbox[3] > result["height"]:
            print(f'    WARNING: y2={bbox[3]} > height={result["height"]}')

print('\n测试完成')
