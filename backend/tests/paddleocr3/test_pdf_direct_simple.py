"""
简单测试 PPStructureV3 是否支持直接处理 PDF 文件
"""
import os
import sys
import time

# 找一个测试 PDF 文件
uploads_dir = "uploads"
pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]

if not pdf_files:
    print("没有找到测试 PDF 文件")
    sys.exit(1)

test_pdf = os.path.join(uploads_dir, pdf_files[0])
print(f"测试 PDF: {test_pdf}")
print(f"文件大小: {os.path.getsize(test_pdf) / 1024:.1f} KB")

# 导入并测试
print("\n导入 PPStructureV3...")
from paddleocr import PPStructureV3

print("创建实例...")
ppstructure = PPStructureV3()

print("\n尝试直接处理 PDF...")
start = time.time()

try:
    result = list(ppstructure.predict(
        test_pdf,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False
    ))
    elapsed = time.time() - start
    print(f"\n✅ 成功！耗时: {elapsed:.2f} 秒")
    print(f"结果数量: {len(result)}")
    
    if result:
        r = result[0]
        print(f"结果类型: {type(r)}")
        if hasattr(r, 'keys'):
            print(f"结果键: {list(r.keys())}")
            
except Exception as e:
    elapsed = time.time() - start
    print(f"\n❌ 失败 (耗时 {elapsed:.2f} 秒): {e}")
