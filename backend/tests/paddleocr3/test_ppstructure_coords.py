"""
测试 PPStructureV3 返回的坐标是基于什么尺寸
"""
from paddleocr import PPStructureV3
from PIL import Image
import os

# 原始图像
img_path = 'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png'
img = Image.open(img_path)
print(f'原始图像尺寸: {img.size}')

# 创建缩小的图像
small_img = img.resize((1447, 2048))
small_path = 'temp/test_small_coords.png'
small_img.save(small_path)
print(f'缩小图像尺寸: {small_img.size}')

# 用 PPStructureV3 处理缩小的图像
print('\n正在加载 PPStructureV3...')
ppstructure = PPStructureV3()

print('\n处理缩小的图像...')
results = list(ppstructure.predict(
    small_path,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False
))

print('\nPPStructureV3 返回的坐标:')
for result in results:
    if hasattr(result, 'parsing_res_list'):
        for block in result.parsing_res_list[:5]:
            bbox = block.bbox
            print(f'  Type: {block.label}, bbox: {bbox}')
            # 检查坐标范围
            if bbox[2] > 1447:
                print(f'    -> x2={bbox[2]} 超出缩小图像宽度 1447!')
            if bbox[3] > 2048:
                print(f'    -> y2={bbox[3]} 超出缩小图像高度 2048!')

# 清理
os.remove(small_path)
print('\n测试完成')
