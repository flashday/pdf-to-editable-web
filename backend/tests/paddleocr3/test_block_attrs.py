"""测试 PPStructureV3 LayoutBlock 的属性"""
from paddleocr import PPStructureV3
import os

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

# 创建 PPStructureV3 实例
ppstructure = PPStructureV3()

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
    
    if hasattr(first_result, 'parsing_res_list'):
        blocks = first_result.parsing_res_list
        print(f'Block count: {len(blocks)}')
        
        for i, block in enumerate(blocks[:5]):  # 只检查前5个
            print(f'\n=== Block {i} ===')
            print(f'Type: {type(block)}')
            print(f'label: {getattr(block, "label", None)}')
            print(f'bbox: {getattr(block, "bbox", None)}')
            content = getattr(block, "content", None)
            if content:
                print(f'content: {str(content)[:100]}...')
            else:
                print(f'content: None')
            
            # 检查所有非私有属性
            print('All attributes:')
            for attr in dir(block):
                if not attr.startswith('_'):
                    val = getattr(block, attr, None)
                    if not callable(val):
                        val_str = str(val)
                        if len(val_str) > 80:
                            val_str = val_str[:80] + '...'
                        print(f'  {attr}: {val_str}')
