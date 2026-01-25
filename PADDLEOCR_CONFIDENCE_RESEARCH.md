# PaddleOCR V3 系列置信度研究报告

## 研究背景

用户反馈当前系统的总体置信度不够可靠，特别是当识别的图像有很多文本块时，由于存在大量无置信度的区域，导致整体置信度计算不准确。

## 核心发现

### 1. PaddleOCR 置信度的两个层面

PaddleOCR 的置信度分为两个独立的层面：

| 层面 | 模型 | 置信度来源 | 当前状态 |
|------|------|-----------|---------|
| **文本检测 (Detection)** | DB 算法 | 检测框的置信度 | ❌ **默认不输出** |
| **文本识别 (Recognition)** | SVTR/CRNN | 字符概率的平均值 | ✅ 正常输出 |

### 2. 为什么检测置信度默认不输出？

根据 [StackOverflow 讨论](https://stackoverflow.com/questions/78841615/paddle-ocr-detection-confidence-level)：

> "The confidence score here is regarding to the recognizer. Is there a way to obtain the confidence score of the detected text?"

**答案**：PaddleOCR 默认只输出**识别置信度**（recognition confidence），而**检测置信度**（detection confidence）需要修改源码才能获取。

### 3. PaddleOCR 3.x 的输出格式

根据官方文档和代码分析，PaddleOCR 3.x 的标准输出格式为：

```python
# 单个文本行的结果格式
[
    [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  # 检测框坐标（4个点）
    ("识别的文本", 0.95)                    # (文本内容, 识别置信度)
]
```

**关键点**：
- `0.95` 是**识别置信度**（rec_score），不是检测置信度
- 检测置信度在 DB 算法的后处理阶段被丢弃了

### 4. 识别置信度的计算方式

根据 PaddleOCR 源码分析，识别置信度的计算方式：

```python
# 在 BaseRecLabelDecode 类的 decode() 方法中
# 置信度 = 所有字符概率的平均值

# CTC 解码时：
# 1. 模型输出每个时间步的字符概率分布
# 2. 取每个时间步最大概率的字符
# 3. 去除重复字符和空白符
# 4. 计算所有保留字符的概率平均值作为置信度
```

### 5. PPStructureV3 的置信度情况（改进前）

| 区域类型 | 置信度来源 | 说明 |
|---------|-----------|------|
| **表格 (table)** | `table_ocr_pred.rec_scores` | 表格内所有单元格 OCR 置信度的平均值 |
| **文本 (text)** | ❌ **无** | PPStructureV3 不输出文本区域的置信度 |
| **图片 (figure)** | ❌ **无** | 无置信度 |
| **标题 (title)** | ❌ **无** | 无置信度 |

**这就是问题所在**：PPStructureV3 的布局分析结果中，只有表格区域有置信度，其他区域都没有！

## 已实施的改进方案

### 改进方案：从 overall_ocr_res 获取文本置信度 ✅ 已实施

PPStructureV3 的返回结果中有 `overall_ocr_res` 字段，包含整页的 OCR 结果：

```python
result = ppstructure.predict(image_path)
for page_result in result:
    overall_ocr_res = page_result.get('overall_ocr_res')
    if overall_ocr_res:
        # overall_ocr_res 包含：
        # - dt_polys: 检测框坐标 (N, 4, 2)
        # - rec_texts: 识别的文本列表
        # - rec_scores: 识别置信度列表
```

### 实施的代码改进

1. **新增 `_extract_ocr_text_lines_with_confidence` 方法**
   - 从 `overall_ocr_res` 提取所有文本行的置信度和位置信息
   - 返回包含 bbox, text, confidence 的文本行列表

2. **新增 `_match_block_confidence_from_ocr` 方法**
   - 根据布局区块的位置，从 OCR 文本行中匹配并计算平均置信度
   - 使用 IoU (Intersection over Union) 和中心点匹配策略
   - IoU > 0.3 或文本行中心点在区块内则认为匹配

3. **修改 `_process_ppstructure_v3_result` 方法**
   - 获取 `overall_ocr_res` 字段
   - 对非表格区块，调用匹配方法获取置信度

4. **改进 `_calculate_confidence_metrics` 方法**
   - 添加更详细的统计信息：
     - `regions_with_confidence`: 有置信度的区域数量
     - `regions_without_confidence`: 无置信度的区域数量
     - `confidence_coverage`: 置信度覆盖率
   - 考虑覆盖率对整体置信度的影响

### 改进后的置信度情况

| 区域类型 | 置信度来源 | 说明 |
|---------|-----------|------|
| **表格 (table)** | `table_ocr_pred.rec_scores` | 表格内所有单元格 OCR 置信度的平均值 |
| **文本 (text)** | ✅ `overall_ocr_res.rec_scores` | 通过位置匹配获取文本行置信度的平均值 |
| **标题 (title)** | ✅ `overall_ocr_res.rec_scores` | 通过位置匹配获取 |
| **图片 (figure)** | ❌ 无 | 图片区域本身没有 OCR 置信度 |

## 参考资料

1. [PaddleOCR 3.0 Technical Report (arXiv)](https://arxiv.org/html/2507.05595v1)
2. [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
3. [StackOverflow: Paddle OCR Detection confidence level](https://stackoverflow.com/questions/78841615/paddle-ocr-detection-confidence-level)
4. [FastDeploy OCR API](https://www.paddlepaddle.org.cn/fastdeploy-api-doc/python/html/ocr.html)
5. [PaddleOCR 官方文档](https://paddlepaddle.github.io/PaddleOCR/)

## 结论

1. **PaddleOCR V3 确实提供了文本块的置信度**，但只是**识别置信度**（rec_score）
2. **检测置信度**（det_score）默认不输出，需要修改源码
3. **PPStructureV3 的问题已解决**：通过从 `overall_ocr_res` 获取置信度并匹配到布局区块
4. **改进效果**：现在大部分文本区域都能获取到置信度，置信度覆盖率大幅提升

---
*研究日期：2026年1月25日*
*PaddleOCR 版本：3.x*
*改进实施：已完成*
