#!/usr/bin/env python
"""
直接测试 PaddleOCR 功能的诊断脚本
"""
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

def test_paddleocr():
    """测试 PaddleOCR 是否正常工作"""
    print("=" * 60)
    print("PaddleOCR 诊断测试")
    print("=" * 60)
    
    try:
        print("\n1. 导入 PaddleOCR...")
        from paddleocr import PaddleOCR
        print("   ✅ PaddleOCR 导入成功")
        
        print("\n2. 初始化 OCR 引擎...")
        ocr = PaddleOCR(use_angle_cls=True, lang='ch', use_gpu=False, show_log=False)
        print("   ✅ OCR 引擎初始化成功")
        
        print("\n3. 初始化 PP-Structure 引擎...")
        structure = PaddleOCR(
            use_angle_cls=True, 
            lang='ch', 
            use_gpu=False, 
            show_log=False,
            use_structure=True
        )
        print("   ✅ PP-Structure 引擎初始化成功")
        
        print("\n4. 创建测试图像...")
        from PIL import Image, ImageDraw, ImageFont
        import os
        
        # 创建一个简单的测试图像
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # 绘制一些文本
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            # 如果找不到字体，使用默认字体
            font = ImageFont.load_default()
        
        draw.text((50, 50), "Hello World", fill='black', font=font)
        draw.text((50, 150), "测试文本", fill='black', font=font)
        draw.text((50, 250), "Test OCR", fill='black', font=font)
        
        # 保存测试图像
        test_image_path = 'test_ocr_image.png'
        img.save(test_image_path)
        print(f"   ✅ 测试图像已创建: {test_image_path}")
        
        print("\n5. 测试 OCR 文本识别...")
        result = ocr.ocr(test_image_path, cls=True)
        print(f"   OCR 结果: {result}")
        
        if result and result[0]:
            print(f"   ✅ OCR 识别成功，识别到 {len(result[0])} 个文本区域")
            for idx, line in enumerate(result[0]):
                text = line[1][0]
                confidence = line[1][1]
                print(f"      区域 {idx+1}: '{text}' (置信度: {confidence:.2f})")
        else:
            print("   ⚠️ OCR 没有识别到任何文本")
        
        print("\n6. 测试 PP-Structure 布局分析...")
        structure_result = structure.ocr(test_image_path, cls=True)
        print(f"   Structure 结果: {structure_result}")
        
        if structure_result and structure_result[0]:
            print(f"   ✅ 布局分析成功，识别到 {len(structure_result[0])} 个区域")
        else:
            print("   ⚠️ 布局分析没有识别到任何区域")
        
        # 清理测试图像
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            print(f"\n   清理测试图像: {test_image_path}")
        
        print("\n" + "=" * 60)
        print("✅ PaddleOCR 诊断测试完成")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_paddleocr()
    sys.exit(0 if success else 1)
