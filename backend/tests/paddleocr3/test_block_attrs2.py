"""测试 PPStructureV3 LayoutBlock 的属性 - 简化版"""
import os
import sys

# 使用已加载的后端实例
sys.path.insert(0, '.')

from backend.services.ocr_service import get_ppstructure_v3_instance

ppstructure = get_ppstructure_v3_instance()
if ppstructure is None:
    print('PPStructureV3 not available, please start backend first')
    exit()

# 找一个测试图像
test_image = None
for f in os.listdir('temp'):
    if f.endswith('_page1.png'):
        test_image = os.path.join('temp', f)
        break

if not test_image:
    print('No test image found')
    exit()

print(f'Testing with: {test_image}')

# 处理图像
result = list(ppstructure.predict(
    test_image,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False
))

print(f'Result count: {len(result)}')

if result:
    first_result = result[0]
    print(f'Result type: {type(first_result)}')
    
    # 检查 overall_ocr_res
    if hasattr(first_result, 'overall_ocr_res'):
        ocr_res = first_result.overall_ocr_res
        print(f'overall_ocr_res type: {type(ocr_res)}')
        if ocr_res:
            print(f'overall_ocr_res length: {len(ocr_res) if hasattr(ocr_res, "__len__") else "N/A"}')
            if isinstance(ocr_res, list) and len(ocr_res) > 0:
                print(f'First OCR item: {ocr_res[0]}')
    
    if hasattr(first_result, 'parsing_res_list'):
        blocks = first_result.parsing_res_list
        print(f'Block count: {len(blocks)}')
        
        for i, block in enumerate(blocks[:3]):
            print(f'\n=== Block {i} ===')
            print(f'label: {getattr(block, "label", None)}')
            
            # 检查所有非私有、非方法属性
            for attr in sorted(dir(block)):
                if not attr.startswith('_'):
                    val = getattr(block, attr, None)
                    if not callable(val):
                        val_str = str(val)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + '...'
                        print(f'  {attr}: {val_str}')
