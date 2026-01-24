# PaddleOCR 3.x 测试脚本
# 这些脚本用于测试 PPStructureV3 的各种功能

"""
测试脚本说明：

1. test_api_confidence.py - 测试 API 返回的置信度数据
2. test_bbox_check.py - 测试边界框坐标
3. test_block_attrs.py / test_block_attrs2.py - 测试 LayoutBlock 属性访问
4. test_confidence_extraction.py - 测试置信度提取逻辑
5. test_markdown_output.py - 测试 Markdown 输出
6. test_ocr_direct.py - 直接测试 OCR 功能
7. test_paddleocr3_api.py - 测试 PaddleOCR 3.x API
8. test_pdf_direct_simple.py - 简单 PDF 处理测试
9. test_ppstructure_coords.py / coords2 / coords3 / coords4 - 坐标系统测试
10. test_ppstructure_pdf_direct.py - PPStructure PDF 直接处理测试
11. test_table_detection.py - 表格检测测试
12. test_end_to_end.py - 端到端测试

运行方式：
    cd backend/tests/paddleocr3
    python test_xxx.py
"""
