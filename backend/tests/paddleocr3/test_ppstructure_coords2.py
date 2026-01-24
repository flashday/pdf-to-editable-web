"""
测试 PPStructureV3 返回的坐标是基于什么尺寸
直接用原始图像测试
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

print('\nPPStructureV3 返回的坐标:')
for result in results:
    if hasattr(result, 'parsing_res_list'):
        print(f'找到 {len(result.parsing_res_list)} 个区域')
        for block in result.parsing_res_list[:5]:
            bbox = block.bbox
            print(f'  Type: {block.label}, bbox: {bbox}')
    else:
        print(f'Result type: {type(result)}')
        print(f'Result attrs: {dir(result)}')

print('\n测试完成')
