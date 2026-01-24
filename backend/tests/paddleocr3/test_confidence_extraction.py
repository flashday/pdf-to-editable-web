"""
测试 PPStructureV3 置信度提取

验证：
1. 表格区块：从 table_res_list[x].table_ocr_pred.rec_scores 获取平均置信度
2. 非表格区块：PPStructureV3 不提供置信度，应为 None
"""
import os
import sys

# 禁用模型源检查以加快启动
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['DNNL_VERBOSE'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_confidence_extraction():
    """测试置信度提取"""
    print("=" * 60)
    print("测试 PPStructureV3 置信度提取")
    print("=" * 60)
    
    from paddleocr import PPStructureV3
    
    # 找一个测试图像
    test_images = [
        'temp/fd834fde-931b-4ff2-b823-4e3f0543651d_page1.png',
        'temp/04551cb5-7bae-4d20-9ac3-e7bbfd1da97b_page1.png',
    ]
    
    test_image = None
    for img in test_images:
        if os.path.exists(img):
            test_image = img
            break
    
    if not test_image:
        print("没有找到测试图像")
        return
    
    print(f"\n测试图像: {test_image}")
    
    # 初始化 PPStructureV3
    print("\n正在初始化 PPStructureV3...")
    structure = PPStructureV3()
    
    # 运行预测
    print("\n正在运行预测...")
    result = list(structure.predict(
        test_image,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_seal_recognition=False,
        use_formula_recognition=False,
        use_chart_recognition=False
    ))
    
    print(f"\n返回结果数量: {len(result)}")
    
    if not result:
        print("没有返回结果")
        return
    
    # 分析第一个结果
    first_result = result[0]
    print(f"\n结果类型: {type(first_result)}")
    
    # 列出所有非下划线开头的属性和方法
    print("\n可用属性和方法:")
    for attr in dir(first_result):
        if not attr.startswith('_'):
            try:
                val = getattr(first_result, attr)
                if callable(val):
                    print(f"   {attr}() - 方法")
                else:
                    val_type = type(val).__name__
                    if isinstance(val, list):
                        print(f"   {attr}: list, 长度 {len(val)}")
                    elif isinstance(val, str) and len(val) > 50:
                        print(f"   {attr}: str, 长度 {len(val)}")
                    else:
                        print(f"   {attr}: {val_type} = {val}")
            except Exception as e:
                print(f"   {attr}: 访问错误 - {e}")
    
    # 尝试访问字典方式
    print("\n尝试字典访问:")
    if hasattr(first_result, 'keys'):
        print(f"   keys: {list(first_result.keys())}")
    if hasattr(first_result, '__getitem__'):
        print("   支持 [] 访问")
        try:
            # 尝试一些常见的键
            for key in ['parsing_res_list', 'table_res_list', 'overall_ocr_res', 'layout_det_res']:
                try:
                    val = first_result[key]
                    print(f"   [{key}]: {type(val).__name__}, 长度 {len(val) if hasattr(val, '__len__') else 'N/A'}")
                except (KeyError, TypeError):
                    pass
        except Exception as e:
            print(f"   访问错误: {e}")
    
    # 检查各个属性
    print("\n" + "=" * 60)
    print("检查结果属性")
    print("=" * 60)
    
    # 1. parsing_res_list - 布局分析结果
    parsing_res_list = getattr(first_result, 'parsing_res_list', None)
    if parsing_res_list:
        print(f"\n1. parsing_res_list: {len(parsing_res_list)} 个区块")
        for idx, block in enumerate(parsing_res_list[:5]):  # 只显示前5个
            label = getattr(block, 'label', 'unknown')
            content = getattr(block, 'content', '')
            content_preview = content[:50] + '...' if len(content) > 50 else content
            
            # 检查是否有 confidence 或 score 属性
            confidence = getattr(block, 'confidence', None)
            score = getattr(block, 'score', None)
            
            print(f"   [{idx}] label={label}, confidence={confidence}, score={score}")
            print(f"       content: {content_preview}")
            
            # 列出所有属性
            attrs = [a for a in dir(block) if not a.startswith('_')]
            print(f"       属性: {attrs}")
    else:
        print("\n1. parsing_res_list: 不存在")
    
    # 2. table_res_list - 表格识别结果
    table_res_list = getattr(first_result, 'table_res_list', None)
    if table_res_list:
        print(f"\n2. table_res_list: {len(table_res_list)} 个表格")
        for idx, table_res in enumerate(table_res_list):
            print(f"\n   === 表格 {idx} ===")
            
            # 检查 table_ocr_pred
            table_ocr_pred = getattr(table_res, 'table_ocr_pred', None)
            if table_ocr_pred is None and hasattr(table_res, 'get'):
                table_ocr_pred = table_res.get('table_ocr_pred', None)
            
            if table_ocr_pred:
                print(f"   table_ocr_pred 类型: {type(table_ocr_pred)}")
                
                # 获取 rec_scores
                if hasattr(table_ocr_pred, 'get'):
                    rec_scores = table_ocr_pred.get('rec_scores', [])
                    rec_texts = table_ocr_pred.get('rec_texts', [])
                elif hasattr(table_ocr_pred, 'rec_scores'):
                    rec_scores = table_ocr_pred.rec_scores
                    rec_texts = getattr(table_ocr_pred, 'rec_texts', [])
                else:
                    rec_scores = []
                    rec_texts = []
                
                print(f"   rec_scores 数量: {len(rec_scores)}")
                print(f"   rec_texts 数量: {len(rec_texts)}")
                
                if rec_scores:
                    avg_confidence = sum(rec_scores) / len(rec_scores)
                    print(f"   平均置信度: {avg_confidence:.4f}")
                    print(f"   置信度范围: {min(rec_scores):.4f} - {max(rec_scores):.4f}")
                    
                    # 显示前几个文本和置信度
                    print(f"   前5个文本和置信度:")
                    for i in range(min(5, len(rec_texts))):
                        text = rec_texts[i] if i < len(rec_texts) else ''
                        score = rec_scores[i] if i < len(rec_scores) else 0
                        print(f"      [{i}] {score:.4f}: {text}")
            else:
                print(f"   table_ocr_pred: 不存在")
            
            # 列出表格结果的所有属性
            if hasattr(table_res, '__dict__'):
                attrs = list(table_res.__dict__.keys())
            elif hasattr(table_res, 'keys'):
                attrs = list(table_res.keys())
            else:
                attrs = [a for a in dir(table_res) if not a.startswith('_')]
            print(f"   表格属性: {attrs}")
    else:
        print("\n2. table_res_list: 不存在或为空")
    
    # 3. overall_ocr_res - 整体 OCR 结果
    overall_ocr_res = getattr(first_result, 'overall_ocr_res', None)
    if overall_ocr_res:
        print(f"\n3. overall_ocr_res 类型: {type(overall_ocr_res)}")
        
        rec_texts = getattr(overall_ocr_res, 'rec_texts', [])
        rec_scores = getattr(overall_ocr_res, 'rec_scores', [])
        
        print(f"   rec_texts 数量: {len(rec_texts)}")
        print(f"   rec_scores 数量: {len(rec_scores)}")
        
        if rec_scores:
            avg_confidence = sum(rec_scores) / len(rec_scores)
            print(f"   平均置信度: {avg_confidence:.4f}")
    else:
        print("\n3. overall_ocr_res: 不存在")
    
    # 4. 列出所有顶级属性
    print("\n" + "=" * 60)
    print("结果对象的所有属性")
    print("=" * 60)
    if hasattr(first_result, '__dict__'):
        for key, value in first_result.__dict__.items():
            val_type = type(value).__name__
            if isinstance(value, list):
                print(f"   {key}: list, 长度 {len(value)}")
            elif isinstance(value, str) and len(value) > 100:
                print(f"   {key}: str, 长度 {len(value)}")
            else:
                print(f"   {key}: {val_type}")


if __name__ == '__main__':
    test_confidence_extraction()
