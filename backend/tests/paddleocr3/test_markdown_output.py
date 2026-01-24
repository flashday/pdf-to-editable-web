"""测试 Markdown 输出功能"""
import sys
sys.path.insert(0, '.')

print("Testing Markdown output...")

# 测试 OCR 服务的 Markdown 输出
from backend.services.ocr_service import PaddleOCRService

service = PaddleOCRService()
print("✅ Service initialized")

# 测试 PPStructureV3 和 Markdown 输出
test_image = "temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png"

try:
    from paddleocr import PPStructureV3
    pp = PPStructureV3()
    result = list(pp.predict(test_image))
    print(f"✅ PPStructureV3 returned {len(result)} items")
    
    # 处理结果
    if result:
        first = result[0]
        print(f"   Keys: {list(first.keys()) if isinstance(first, dict) else 'not dict'}")
        
        # 生成 Markdown
        processed = service._process_ppstructure_v3_result(result, test_image)
        print(f"✅ Processed {len(processed)} items")
        
        md_content = service.generate_markdown_output(test_image, processed)
        print(f"✅ Generated Markdown ({len(md_content)} chars)")
        print("\n--- Markdown Preview (first 500 chars) ---")
        print(md_content[:500])
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 测试 data_normalizer 的 Markdown → Block 转换
print("\n--- Testing Markdown to Block conversion ---")
from backend.services.data_normalizer import DataNormalizer

normalizer = DataNormalizer()

test_markdown = """# 测试标题

这是一段普通文本。

## 二级标题

| 列1 | 列2 | 列3 |
| --- | --- | --- |
| A | B | C |
| D | E | F |

- 列表项1
- 列表项2
- 列表项3

> 这是引用文本

*斜体文本*
"""

try:
    editor_data = normalizer.normalize_markdown_to_blocks(test_markdown)
    print(f"✅ Converted to {len(editor_data.blocks)} blocks")
    
    for i, block in enumerate(editor_data.blocks[:5]):
        print(f"   Block {i}: type={block.type}, data={str(block.data)[:50]}...")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All tests completed!")
