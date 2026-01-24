"""
PaddleOCR 3.x API 测试脚本
用于验证新 API 的输出格式
"""
import os
import sys

# 禁用模型源检查以加快启动
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# 禁用 oneDNN 以避免兼容性问题
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['DNNL_VERBOSE'] = '0'

# 设置 Paddle 使用 CPU
os.environ['CUDA_VISIBLE_DEVICES'] = ''

def test_paddleocr_basic():
    """测试基础 PaddleOCR API"""
    print("=" * 50)
    print("测试 PaddleOCR 3.x 基础 OCR")
    print("=" * 50)
    
    from paddleocr import PaddleOCR
    
    # 初始化 OCR 引擎
    ocr = PaddleOCR(lang='ch')
    print(f"PaddleOCR 初始化成功")
    print(f"OCR 类型: {type(ocr)}")
    print(f"OCR 方法: {[m for m in dir(ocr) if not m.startswith('_')]}")
    
    # 测试图片路径
    test_images = [
        'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png',
        'temp/31cd2ea0-b666-42de-b448-7a9b5404dc14_page1.png'
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n测试图片: {img_path}")
            try:
                # 使用 predict 方法（3.x 新 API）
                result = ocr.predict(img_path)
                print(f"结果类型: {type(result)}")
                
                # 检查结果结构
                if hasattr(result, '__iter__'):
                    for idx, item in enumerate(result):
                        print(f"  Item {idx} 类型: {type(item)}")
                        if hasattr(item, 'keys'):
                            print(f"  Item {idx} keys: {list(item.keys())}")
                        if idx >= 2:
                            print("  ... (更多结果省略)")
                            break
                
                print("基础 OCR 测试成功!")
                return True
            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()
    
    print("未找到测试图片")
    return False


def test_ppstructurev3():
    """测试 PPStructureV3 API"""
    print("\n" + "=" * 50)
    print("测试 PPStructureV3")
    print("=" * 50)
    
    from paddleocr import PPStructureV3
    
    # 初始化 PPStructureV3
    structure = PPStructureV3(
        lang='ch',
        use_table_recognition=True,
        use_formula_recognition=False,  # 暂时禁用公式识别
        use_chart_recognition=False,    # 暂时禁用图表识别
    )
    print(f"PPStructureV3 初始化成功")
    print(f"Structure 类型: {type(structure)}")
    print(f"Structure 方法: {[m for m in dir(structure) if not m.startswith('_')]}")
    
    # 测试图片路径
    test_images = [
        'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png',
        'temp/31cd2ea0-b666-42de-b448-7a9b5404dc14_page1.png'
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n测试图片: {img_path}")
            try:
                # 使用 predict 方法
                result = structure.predict(img_path)
                print(f"结果类型: {type(result)}")
                
                # 检查结果结构
                if hasattr(result, '__iter__'):
                    for idx, item in enumerate(result):
                        print(f"\n  === Item {idx} ===")
                        print(f"  类型: {type(item)}")
                        
                        if hasattr(item, 'keys'):
                            print(f"  Keys: {list(item.keys())}")
                            
                            # 打印每个 key 的值类型
                            for key in item.keys():
                                val = item[key]
                                val_type = type(val).__name__
                                if isinstance(val, str) and len(val) > 100:
                                    print(f"    {key}: {val_type} (长度: {len(val)})")
                                elif isinstance(val, list) and len(val) > 5:
                                    print(f"    {key}: {val_type} (长度: {len(val)})")
                                else:
                                    print(f"    {key}: {val_type} = {val}")
                        
                        if idx >= 3:
                            print("\n  ... (更多结果省略)")
                            break
                
                print("\nPPStructureV3 测试成功!")
                return True
            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()
    
    print("未找到测试图片")
    return False


def test_markdown_output():
    """测试 Markdown 输出功能"""
    print("\n" + "=" * 50)
    print("测试 Markdown 输出")
    print("=" * 50)
    
    from paddleocr import PPStructureV3
    
    structure = PPStructureV3(lang='ch')
    
    test_images = [
        'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png',
    ]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            print(f"\n测试图片: {img_path}")
            try:
                result = structure.predict(img_path)
                
                # 检查是否有 markdown 输出
                for idx, item in enumerate(result):
                    if hasattr(item, 'keys'):
                        if 'markdown' in item:
                            print(f"\n找到 Markdown 输出:")
                            md = item['markdown']
                            print(f"  长度: {len(md)}")
                            print(f"  前 500 字符:\n{md[:500]}")
                        if 'html' in item:
                            print(f"\n找到 HTML 输出:")
                            html = item['html']
                            print(f"  长度: {len(html)}")
                            print(f"  前 500 字符:\n{html[:500]}")
                
                return True
            except Exception as e:
                print(f"错误: {e}")
                import traceback
                traceback.print_exc()
    
    return False


if __name__ == '__main__':
    print("PaddleOCR 3.x API 测试")
    print("=" * 60)
    
    # 测试基础 OCR
    test_paddleocr_basic()
    
    # 测试 PPStructureV3
    test_ppstructurev3()
    
    # 测试 Markdown 输出
    test_markdown_output()
    
    print("\n" + "=" * 60)
    print("测试完成")
