"""
输出生成模块

负责生成各种格式的输出：
- HTML 输出（可编辑）
- Markdown 输出
- 置信度日志
- 原始 OCR JSON 输出
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class OutputGenerator:
    """输出生成器"""
    
    def __init__(self):
        pass
    
    def generate_editable_html(self, image_path: str, ppstructure_result: List[Dict]) -> str:
        """
        生成可编辑的 HTML 内容
        
        每个区域包含 data-region-id, data-region-type, data-bbox 属性
        
        Args:
            image_path: 原始图像路径
            ppstructure_result: PPStructure 处理结果
            
        Returns:
            HTML 字符串
        """
        # 提取 job_id
        job_id = self._extract_job_id(image_path)
        
        # 按 y 坐标排序（从上到下阅读顺序）
        sorted_results = sorted(ppstructure_result, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
        
        html_parts = []
        
        for idx, item in enumerate(sorted_results):
            item_type = item.get('type', 'unknown')
            res = item.get('res', {})
            bbox = item.get('bbox', [0, 0, 0, 0])
            
            # 创建 bbox JSON
            bbox_data = json.dumps({
                'x': float(bbox[0]), 
                'y': float(bbox[1]), 
                'x2': float(bbox[2]), 
                'y2': float(bbox[3])
            })
            
            html_content = self._generate_html_for_item(idx, item_type, res, bbox_data)
            if html_content:
                html_parts.append(html_content)
        
        return '\n'.join(html_parts)
    
    def _generate_html_for_item(self, idx: int, item_type: str, res: Any, bbox_data: str) -> str:
        """为单个项目生成 HTML"""
        text_content = self._extract_text_from_res(res)
        
        type_handlers = {
            'table': self._html_table_item,
            'title': lambda i, t, b: self._html_text_item(i, t, b, 'title'),
            'text': lambda i, t, b: self._html_text_item(i, t, b, 'text-block'),
            'header': lambda i, t, b: self._html_text_item(i, t, b, 'header'),
            'footer': lambda i, t, b: self._html_text_item(i, t, b, 'footer'),
            'figure': lambda i, t, b: f'<div class="ocr-region figure-placeholder" data-region-id="{i}" data-region-type="figure" data-bbox=\'{b}\'>[图像]</div>',
            'figure_caption': lambda i, t, b: self._html_text_item(i, t, b, 'figure-caption'),
            'table_caption': lambda i, t, b: self._html_text_item(i, t, b, 'table-caption'),
            'reference': lambda i, t, b: self._html_text_item(i, t, b, 'reference'),
            'equation': lambda i, t, b: self._html_equation_item(i, t, b),
        }
        
        handler = type_handlers.get(item_type)
        if handler:
            if item_type == 'table':
                return handler(idx, res, bbox_data)
            else:
                return handler(idx, text_content, bbox_data) if text_content else ''
        else:
            return self._html_text_item(idx, text_content, bbox_data, 'text-block') if text_content else ''
    
    def _html_table_item(self, idx: int, res: Any, bbox_data: str) -> str:
        """生成表格 HTML"""
        if isinstance(res, dict) and 'html' in res:
            table_html = res['html']
            table_html = table_html.replace('<html>', '').replace('</html>', '')
            table_html = table_html.replace('<body>', '').replace('</body>', '')
            return (f'<div class="ocr-region table-wrapper" data-region-id="{idx}" '
                   f'data-region-type="table" data-bbox=\'{bbox_data}\'>\n{table_html.strip()}\n</div>')
        elif isinstance(res, str):
            return (f'<div class="ocr-region table-wrapper" data-region-id="{idx}" '
                   f'data-region-type="table" data-bbox=\'{bbox_data}\'>\n{res}\n</div>')
        return ''
    
    def _html_text_item(self, idx: int, text: str, bbox_data: str, css_class: str) -> str:
        """生成文本 HTML"""
        return (f'<div class="ocr-region {css_class}" data-region-id="{idx}" '
               f'data-region-type="text" data-bbox=\'{bbox_data}\'>\n'
               f'<span class="editable-content">{text}</span>\n</div>')
    
    def _html_equation_item(self, idx: int, text: str, bbox_data: str) -> str:
        """生成公式 HTML"""
        return (f'<div class="ocr-region equation" data-region-id="{idx}" '
               f'data-region-type="text" data-bbox=\'{bbox_data}\'>\n'
               f'<span class="editable-content"><em>{text}</em></span>\n</div>')
    
    def generate_markdown(self, image_path: str, ppstructure_result: List[Dict], save_file: bool = True) -> str:
        """
        生成 Markdown 输出
        
        Args:
            image_path: 原始图像路径
            ppstructure_result: PPStructure 处理结果
            save_file: 是否保存到文件
            
        Returns:
            Markdown 字符串
        """
        job_id = self._extract_job_id(image_path)
        
        # 按 y 坐标排序
        sorted_results = sorted(ppstructure_result, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
        
        markdown_parts = []
        
        for item in sorted_results:
            item_type = item.get('type', 'unknown')
            res = item.get('res', {})
            
            md_content = self._generate_markdown_for_item(item_type, res)
            if md_content:
                markdown_parts.append(md_content)
                markdown_parts.append("")  # 空行分隔
        
        markdown_content = '\n'.join(markdown_parts)
        
        # 保存文件
        if save_file:
            output_folder = Path(image_path).parent
            md_path = output_folder / f"{job_id}_raw_ocr.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"Saved Markdown to: {md_path}")
        
        return markdown_content
    
    def _generate_markdown_for_item(self, item_type: str, res: Any) -> str:
        """为单个项目生成 Markdown"""
        text_content = self._extract_text_from_res(res)
        
        type_handlers = {
            'title': lambda t: f"# {t}" if t else '',
            'text': lambda t: t if t else '',
            'header': lambda t: f"*{t}*" if t else '',
            'footer': lambda t: f"*{t}*" if t else '',
            'table': lambda r: self._table_to_markdown(r),
            'figure': lambda t: "![图像]()",
            'figure_caption': lambda t: f"*图: {t}*" if t else '',
            'table_caption': lambda t: f"*表: {t}*" if t else '',
            'reference': lambda t: f"> {t}" if t else '',
            'equation': lambda t: f"${t}$" if t else '',
        }
        
        handler = type_handlers.get(item_type)
        if handler:
            if item_type == 'table':
                return handler(res)
            else:
                return handler(text_content)
        else:
            return text_content if text_content else ''
    
    def _table_to_markdown(self, table_res: Any) -> str:
        """将表格转换为 Markdown 格式"""
        try:
            if isinstance(table_res, dict) and 'html' in table_res:
                return self._html_table_to_markdown(table_res['html'])
            if isinstance(table_res, list):
                return self._list_to_markdown_table(table_res)
            return ""
        except Exception as e:
            logger.warning(f"Failed to convert table to Markdown: {e}")
            return ""
    
    def _html_table_to_markdown(self, html_content: str) -> str:
        """将 HTML 表格转换为 Markdown"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return ""
            
            rows = table.find_all('tr')
            if not rows:
                return ""
            
            markdown_rows = []
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                cell_texts = [cell.get_text(strip=True).replace('|', '\\|') for cell in cells]
                
                markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
                
                # 第一行后添加分隔符
                if row_idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
                    markdown_rows.append(separator)
            
            return '\n'.join(markdown_rows)
            
        except ImportError:
            logger.warning("BeautifulSoup not available")
            return ""
        except Exception as e:
            logger.warning(f"HTML table to Markdown failed: {e}")
            return ""
    
    def _list_to_markdown_table(self, table_data: List) -> str:
        """将列表数据转换为 Markdown 表格"""
        if not table_data:
            return ""
        
        markdown_rows = []
        
        for row_idx, row in enumerate(table_data):
            if isinstance(row, list):
                cell_texts = [str(cell).replace('|', '\\|') for cell in row]
                markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
                
                if row_idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
                    markdown_rows.append(separator)
        
        return '\n'.join(markdown_rows)
    
    def save_raw_ocr_json(self, image_path: str, structure_result: List, scale_info: Dict[str, Any]) -> None:
        """
        保存原始 OCR JSON 输出
        
        Args:
            image_path: 原始图像路径
            structure_result: OCR 结果
            scale_info: 缩放信息
        """
        try:
            job_id = self._extract_job_id(image_path)
            output_folder = Path(image_path).parent
            
            raw_json_data = {
                'job_id': job_id,
                'image_path': str(image_path),
                'scale_info': scale_info,
                'ocr_result': []
            }
            
            if structure_result and len(structure_result) > 0:
                actual_results = structure_result[0] if structure_result else []
                
                for idx, item in enumerate(actual_results):
                    if not item or len(item) < 2:
                        continue
                    
                    try:
                        bbox_coords = item[0]
                        text_info = item[1]
                        
                        if isinstance(text_info, tuple) and len(text_info) >= 2:
                            text_content = text_info[0]
                            confidence = float(text_info[1])
                        else:
                            text_content = str(text_info)
                            confidence = 0.0
                        
                        x_coords = [point[0] for point in bbox_coords]
                        y_coords = [point[1] for point in bbox_coords]
                        bbox = {
                            'x': min(x_coords),
                            'y': min(y_coords),
                            'width': max(x_coords) - min(x_coords),
                            'height': max(y_coords) - min(y_coords),
                            'points': [[float(p[0]), float(p[1])] for p in bbox_coords]
                        }
                        
                        raw_json_data['ocr_result'].append({
                            'index': idx,
                            'text': text_content,
                            'confidence': confidence,
                            'bbox': bbox
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to process OCR item {idx}: {e}")
            
            json_path = output_folder / f"{job_id}_raw_ocr.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(raw_json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved raw OCR JSON to: {json_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save raw OCR output: {e}")
    
    def save_ppstructure_json(self, image_path: str, ppstructure_result: List[Dict], 
                              scale_info: Dict[str, Any], start_time: Optional[float] = None) -> None:
        """
        保存 PPStructure JSON 输出
        
        Args:
            image_path: 原始图像路径
            ppstructure_result: PPStructure 结果
            scale_info: 缩放信息
            start_time: 处理开始时间
        """
        try:
            job_id = self._extract_job_id(image_path)
            output_folder = Path(image_path).parent
            
            current_time = time.time()
            start_datetime = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S') if start_time else None
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elapsed_time = f"{current_time - start_time:.2f}s" if start_time else None
            
            ppstructure_json_data = {
                'job_id': job_id,
                'image_path': str(image_path),
                'processing_info': {
                    'start_time': start_datetime,
                    'save_time': current_datetime,
                    'elapsed_at_save': elapsed_time
                },
                'scale_info': scale_info,
                'total_items': len(ppstructure_result),
                'items': []
            }
            
            for idx, item in enumerate(ppstructure_result):
                item_data = {
                    'index': idx,
                    'type': item.get('type', 'unknown'),
                    'bbox': item.get('bbox', []),
                    'res': self._serialize_res(item.get('res', {}))
                }
                ppstructure_json_data['items'].append(item_data)
            
            json_path = output_folder / f"{job_id}_ppstructure.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(ppstructure_json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved PPStructure JSON to: {json_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save PPStructure JSON: {e}")
    
    def _serialize_res(self, res: Any) -> Any:
        """序列化 res 字段"""
        if isinstance(res, dict):
            return {
                'html': res.get('html', ''),
                'cell_bbox': res.get('cell_bbox', []),
                'confidence': res.get('confidence', None)
            }
        elif isinstance(res, list):
            serialized = []
            for text_item in res:
                if isinstance(text_item, dict):
                    serialized.append({
                        'text': text_item.get('text', ''),
                        'confidence': text_item.get('confidence', None)
                    })
                else:
                    serialized.append(str(text_item))
            return serialized
        else:
            return str(res) if res else None
    
    def _extract_text_from_res(self, res: Any) -> str:
        """从 res 字段提取文本内容"""
        if isinstance(res, str):
            return res.strip()
        
        if isinstance(res, list):
            texts = []
            for item in res:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item['text'])
                elif isinstance(item, str):
                    texts.append(item)
            return ' '.join(texts)
        
        if isinstance(res, dict):
            if 'text' in res:
                return res['text']
            # 表格类型没有直接的文本
            return ''
        
        return str(res) if res else ''
    
    def _extract_job_id(self, image_path: str) -> str:
        """从图像路径提取 job_id"""
        image_name = Path(image_path).stem
        if '_page' in image_name:
            return image_name.split('_page')[0]
        return image_name
