"""
置信度日志生成模块

负责生成详细的置信度计算日志（Markdown 格式）
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.models.document import Region

logger = logging.getLogger(__name__)


class ConfidenceLogger:
    """置信度日志生成器"""
    
    def __init__(self):
        pass
    
    def generate_confidence_log(self, regions: List[Region], job_id: str, output_folder: str,
                                 start_time: float = None, end_time: float = None,
                                 processing_time: float = None) -> str:
        """
        生成详细的置信度计算日志（Markdown 格式）
        
        Args:
            regions: 识别的区域列表
            job_id: 任务 ID
            output_folder: 输出文件夹路径
            start_time: OCR 处理开始时间戳
            end_time: OCR 处理结束时间戳
            processing_time: 处理耗时（秒）
            
        Returns:
            生成的日志文件路径
        """
        lines = []
        lines.append("# 置信度计算详细日志")
        lines.append("")
        lines.append(f"**任务 ID**: `{job_id}`")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 处理时间信息
        lines.append("---")
        lines.append("## 处理时间信息")
        lines.append("")
        if start_time:
            lines.append(f"- **开始时间**: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if end_time:
            lines.append(f"- **结束时间**: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if processing_time is not None:
            lines.append(f"- **处理耗时**: {processing_time:.2f}s")
        lines.append("")
        
        # 区域概览
        lines.append("---")
        lines.append("## 1. 区域概览")
        lines.append("")
        lines.append(f"- **总区域数**: {len(regions)}")
        
        regions_with_conf = [r for r in regions if r.confidence is not None and r.confidence > 0]
        regions_without_conf = [r for r in regions if r.confidence is None or r.confidence <= 0]
        
        lines.append(f"- **有置信度的区域**: {len(regions_with_conf)}")
        lines.append(f"- **无置信度的区域**: {len(regions_without_conf)}")
        lines.append(f"- **置信度覆盖率**: {len(regions_with_conf) / len(regions) * 100:.1f}%" if regions else "- **置信度覆盖率**: 0%")
        lines.append("")
        
        # 各区域置信度详情
        lines.append("---")
        lines.append("## 2. 各区域置信度详情")
        lines.append("")
        
        if not regions:
            lines.append("*无识别区域*")
        else:
            lines.append("| 序号 | 类型 | 位置 (x,y) | 尺寸 (w×h) | 置信度 | 内容预览 |")
            lines.append("|------|------|------------|------------|--------|----------|")
            
            for i, region in enumerate(regions):
                conf_str = f"{region.confidence}" if region.confidence is not None else "无"
                content_preview = (region.content[:30] + "...") if region.content and len(region.content) > 30 else (region.content or "")
                content_preview = content_preview.replace("|", "\\|").replace("\n", " ")
                
                lines.append(f"| {i+1} | {region.classification.value} | ({region.coordinates.x:.0f}, {region.coordinates.y:.0f}) | {region.coordinates.width:.0f}×{region.coordinates.height:.0f} | {conf_str} | {content_preview} |")
        
        lines.append("")
        
        # 文本置信度计算
        lines.append("---")
        lines.append("## 3. 文本置信度计算")
        lines.append("")
        
        text_confidences = [r.confidence for r in regions_with_conf]
        
        if text_confidences:
            lines.append("### 3.1 有效置信度值列表")
            lines.append("")
            lines.append("```")
            for i, conf in enumerate(text_confidences):
                lines.append(f"  区域 {i+1}: {conf}")
            lines.append("```")
            lines.append("")
            
            text_confidence = sum(text_confidences) / len(text_confidences)
            lines.append("### 3.2 计算过程")
            lines.append("")
            lines.append("```")
            lines.append(f"文本置信度 = 所有有效置信度的平均值")
            lines.append(f"           = ({' + '.join([f'{c}' for c in text_confidences])}) / {len(text_confidences)}")
            lines.append(f"           = {sum(text_confidences)} / {len(text_confidences)}")
            lines.append(f"           = {text_confidence}")
            lines.append("```")
        else:
            text_confidence = 0.0
            lines.append("*无有效置信度数据，文本置信度 = 0.0*")
        
        lines.append("")
        
        # 布局置信度计算
        lines.append("---")
        lines.append("## 4. 布局置信度计算")
        lines.append("")
        
        if not regions:
            layout_confidence = 0.0
            lines.append("*无区域数据，布局置信度 = 0.0*")
        else:
            region_types = set(r.classification for r in regions)
            num_types = len(region_types)
            if num_types >= 3:
                type_diversity = 1.0
            elif num_types == 2:
                type_diversity = 0.9
            else:
                type_diversity = 0.7
            
            lines.append("### 4.1 类型多样性因子")
            lines.append("")
            lines.append(f"- 检测到的区域类型: {', '.join([t.value for t in region_types])}")
            lines.append(f"- 类型数量: {num_types}")
            lines.append(f"- 多样性评分规则: ≥3种类型=1.0, 2种类型=0.9, 1种类型=0.7")
            lines.append(f"- **类型多样性因子**: {type_diversity:.2f}")
            lines.append("")
            
            reasonable_sizes = 0
            for region in regions:
                area = region.coordinates.width * region.coordinates.height
                if 50 < area < 10000000:
                    reasonable_sizes += 1
            size_factor = reasonable_sizes / len(regions)
            
            lines.append("### 4.2 尺寸合理性因子")
            lines.append("")
            lines.append(f"- 合理尺寸范围: 50 < 面积 < 10,000,000 像素")
            lines.append(f"- 合理尺寸区域数: {reasonable_sizes} / {len(regions)}")
            lines.append(f"- **尺寸合理性因子**: {size_factor}")
            lines.append("")
            
            meaningful_content = 0
            for region in regions:
                if region.content and len(region.content.strip()) > 3:
                    meaningful_content += 1
            content_factor = meaningful_content / len(regions)
            
            lines.append("### 4.3 内容质量因子")
            lines.append("")
            lines.append(f"- 有效内容标准: 内容长度 > 3 字符")
            lines.append(f"- 有效内容区域数: {meaningful_content} / {len(regions)}")
            lines.append(f"- **内容质量因子**: {content_factor}")
            lines.append("")
            
            layout_confidence = content_factor * 0.5 + size_factor * 0.3 + type_diversity * 0.2
            
            lines.append("### 4.4 布局置信度计算")
            lines.append("")
            lines.append("```")
            lines.append("布局置信度 = 内容质量因子 × 0.5 + 尺寸合理性因子 × 0.3 + 类型多样性因子 × 0.2")
            lines.append(f"           = {content_factor} × 0.5 + {size_factor} × 0.3 + {type_diversity} × 0.2")
            lines.append(f"           = {content_factor * 0.5} + {size_factor * 0.3} + {type_diversity * 0.2}")
            lines.append(f"           = {layout_confidence}")
            lines.append("```")
        
        lines.append("")
        
        # 总体置信度计算
        lines.append("---")
        lines.append("## 5. 总体置信度计算")
        lines.append("")
        
        if not regions:
            overall_confidence = 0.0
            lines.append("*无区域数据，总体置信度 = 0.0*")
        else:
            confidence_coverage = len(regions_with_conf) / len(regions)
            base_confidence = text_confidence * 0.7 + layout_confidence * 0.3
            coverage_penalty = min(1.0, confidence_coverage / 0.5) if confidence_coverage < 0.5 else 1.0
            overall_confidence = base_confidence * (0.5 + 0.5 * coverage_penalty)
            
            lines.append("### 5.1 基础置信度")
            lines.append("")
            lines.append("```")
            lines.append("基础置信度 = 文本置信度 × 0.7 + 布局置信度 × 0.3")
            lines.append(f"           = {text_confidence} × 0.7 + {layout_confidence} × 0.3")
            lines.append(f"           = {text_confidence * 0.7} + {layout_confidence * 0.3}")
            lines.append(f"           = {base_confidence}")
            lines.append("```")
            lines.append("")
            
            lines.append("### 5.2 覆盖率惩罚")
            lines.append("")
            lines.append(f"- 置信度覆盖率: {confidence_coverage} ({confidence_coverage * 100:.1f}%)")
            lines.append(f"- 惩罚规则: 覆盖率 < 50% 时开始惩罚")
            if confidence_coverage < 0.5:
                lines.append(f"- 惩罚因子 = min(1.0, {confidence_coverage} / 0.5) = {coverage_penalty}")
            else:
                lines.append(f"- 覆盖率 ≥ 50%，无惩罚，惩罚因子 = 1.0")
            lines.append("")
            
            lines.append("### 5.3 最终计算")
            lines.append("")
            lines.append("```")
            lines.append("总体置信度 = 基础置信度 × (0.5 + 0.5 × 惩罚因子)")
            lines.append(f"           = {base_confidence} × (0.5 + 0.5 × {coverage_penalty})")
            lines.append(f"           = {base_confidence} × {0.5 + 0.5 * coverage_penalty}")
            lines.append(f"           = {overall_confidence}")
            lines.append("```")
        
        lines.append("")
        
        # 结果汇总
        lines.append("---")
        lines.append("## 6. 结果汇总")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 总区域数 | {len(regions)} |")
        lines.append(f"| 有置信度区域 | {len(regions_with_conf)} |")
        lines.append(f"| 无置信度区域 | {len(regions_without_conf)} |")
        lines.append(f"| 置信度覆盖率 | {len(regions_with_conf) / len(regions) * 100:.1f}% |" if regions else "| 置信度覆盖率 | 0% |")
        lines.append(f"| 文本置信度 | {text_confidence} |")
        lines.append(f"| 布局置信度 | {layout_confidence if regions else 0.0} |")
        lines.append(f"| **总体置信度** | **{overall_confidence if regions else 0.0}** |")
        lines.append("")
        
        # 保存文件
        log_content = '\n'.join(lines)
        log_path = Path(output_folder) / f"{job_id}_confidence_log.md"
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            logger.info(f"置信度日志已保存到: {log_path}")
        except Exception as e:
            logger.warning(f"保存置信度日志失败: {e}")
        
        return str(log_path)
