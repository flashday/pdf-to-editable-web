"""
测试 PPStructureV3 是否支持直接处理 PDF 文件

目的：验证是否可以跳过手动 PDF 转图像步骤，直接让 PPStructureV3 处理 PDF
"""
import os
import sys
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ppstructure_pdf_direct():
    """测试 PPStructureV3 直接处理 PDF"""
    
    # 找一个测试 PDF 文件
    uploads_dir = "uploads"
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("没有找到测试 PDF 文件")
        return
    
    # 使用第一个 PDF 文件
    test_pdf = os.path.join(uploads_dir, pdf_files[0])
    print(f"测试 PDF 文件: {test_pdf}")
    print(f"文件大小: {os.path.getsize(test_pdf) / 1024:.1f} KB")
    
    # 导入 PPStructureV3
    print("\n正在导入 PPStructureV3...")
    from paddleocr import PPStructureV3
    
    # 获取缓存的实例（如果后端已加载）
    from backend.services.ocr_service import get_ppstructure_v3_instance
    
    ppstructure = get_ppstructure_v3_instance()
    if ppstructure is None:
        print("PPStructureV3 实例不可用，创建新实例...")
        ppstructure = PPStructureV3()
    else:
        print("使用缓存的 PPStructureV3 实例")
    
    # 测试 1: 直接传入 PDF 文件路径
    print("\n" + "=" * 60)
    print("测试 1: 直接传入 PDF 文件路径")
    print("=" * 60)
    
    try:
        start_time = time.time()
        
        # 尝试直接处理 PDF
        result = list(ppstructure.predict(
            test_pdf,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_seal_recognition=False,
            use_formula_recognition=False,
            use_chart_recognition=False
        ))
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ 成功！直接处理 PDF 耗时: {elapsed:.2f} 秒")
        print(f"返回结果数量: {len(result)}")
        
        # 分析结果结构
        if result:
            first_result = result[0]
            print(f"\n结果类型: {type(first_result)}")
            
            if hasattr(first_result, '__dict__'):
                print(f"结果属性: {list(first_result.__dict__.keys())}")
            elif isinstance(first_result, dict):
                print(f"结果键: {list(first_result.keys())}")
            
            # 尝试获取更多信息
            if hasattr(first_result, 'keys'):
                for key in first_result.keys():
                    val = first_result[key]
                    if isinstance(val, list):
                        print(f"  {key}: list, 长度 {len(val)}")
                    elif isinstance(val, str) and len(val) > 100:
                        print(f"  {key}: str, 长度 {len(val)}")
                    else:
                        print(f"  {key}: {type(val).__name__}")
        
        return True, elapsed
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def test_image_vs_pdf_performance():
    """比较图像输入和 PDF 输入的性能"""
    
    # 找一个测试 PDF 文件
    uploads_dir = "uploads"
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("没有找到测试 PDF 文件")
        return
    
    test_pdf = os.path.join(uploads_dir, pdf_files[0])
    job_id = os.path.splitext(pdf_files[0])[0]
    
    # 检查是否有对应的图像文件
    temp_dir = "temp"
    image_path = os.path.join(temp_dir, f"{job_id}_page1.png")
    
    if not os.path.exists(image_path):
        print(f"没有找到对应的图像文件: {image_path}")
        print("请先通过前端上传 PDF 生成图像文件")
        return
    
    print(f"\n测试文件:")
    print(f"  PDF: {test_pdf} ({os.path.getsize(test_pdf) / 1024:.1f} KB)")
    print(f"  图像: {image_path} ({os.path.getsize(image_path) / 1024:.1f} KB)")
    
    from backend.services.ocr_service import get_ppstructure_v3_instance
    ppstructure = get_ppstructure_v3_instance()
    
    if ppstructure is None:
        print("PPStructureV3 不可用")
        return
    
    # 测试图像输入
    print("\n" + "=" * 60)
    print("测试图像输入性能")
    print("=" * 60)
    
    start_time = time.time()
    result_image = list(ppstructure.predict(
        image_path,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False
    ))
    image_time = time.time() - start_time
    print(f"图像输入耗时: {image_time:.2f} 秒")
    
    # 测试 PDF 输入
    print("\n" + "=" * 60)
    print("测试 PDF 输入性能")
    print("=" * 60)
    
    start_time = time.time()
    result_pdf = list(ppstructure.predict(
        test_pdf,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False
    ))
    pdf_time = time.time() - start_time
    print(f"PDF 输入耗时: {pdf_time:.2f} 秒")
    
    # 比较结果
    print("\n" + "=" * 60)
    print("性能比较")
    print("=" * 60)
    print(f"图像输入: {image_time:.2f} 秒")
    print(f"PDF 输入:  {pdf_time:.2f} 秒")
    print(f"差异: {abs(pdf_time - image_time):.2f} 秒 ({'+' if pdf_time > image_time else '-'}{abs(pdf_time - image_time) / image_time * 100:.1f}%)")


if __name__ == "__main__":
    print("=" * 60)
    print("PPStructureV3 PDF 直接输入测试")
    print("=" * 60)
    
    success, elapsed = test_ppstructure_pdf_direct()
    
    if success:
        print("\n\n")
        test_image_vs_pdf_performance()
