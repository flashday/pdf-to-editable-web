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
    print(f'Result type: {type(result)}')
    print(f'Result keys: {result.keys() if hasattr(result, "keys") else "N/A"}')
    
    # 尝试访问不同的属性
    if hasattr(result, 'parsing_res_list'):
        print(f'parsing_res_list: {len(result.parsing_res_list)} items')
    
    # 检查是否是字典类型
    if isinstance(result, dict):
        for key in list(result.keys())[:5]:
            val = result[key]
            print(f'  {key}: {type(val)}')
            if hasattr(val, '__len__') and len(val) > 0:
                print(f'    First item: {val[0] if hasattr(val, "__getitem__") else val}')
    
    # 尝试直接访问 layout_det_res
    if 'layout_det_res' in result:
        layout_res = result['layout_det_res']
        print(f'\nlayout_det_res type: {type(layout_res)}')
        if hasattr(layout_res, 'boxes'):
            print(f'boxes: {layout_res.boxes[:3]}')

print('\n测试完成')
