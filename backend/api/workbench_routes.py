"""
精准作业台 API 路由
提供 React + Markdown 精准作业台所需的后端 API

端点：
- GET /api/convert/{jobId}/layout-with-anchors - 获取带锚点的布局数据
- GET /api/convert/{jobId}/markdown-with-anchors - 获取带锚点的 Markdown
- POST /api/convert/{jobId}/save-markdown - 保存修正后的 Markdown
"""
import os
import json
import time
import logging
from pathlib import Path
from flask import request, jsonify, current_app
from backend.api import api_bp

logger = logging.getLogger(__name__)


# ============================================================
# 布局数据 API
# ============================================================

@api_bp.route('/convert/<job_id>/layout-with-anchors', methods=['GET'])
def get_layout_with_anchors(job_id):
    """
    获取带锚点的布局数据
    
    从 ppstructure.json 提取 Block 数据，生成唯一 Block ID，
    返回标准化的布局数据格式供前端渲染 Bounding Box。
    
    Response:
    {
        "success": true,
        "data": {
            "blocks": [
                {
                    "id": "block_001",
                    "type": "title",
                    "bbox": { "x": 100, "y": 50, "width": 400, "height": 30 },
                    "confidence": 0.95,
                    "pageNum": 1,
                    "text": "文档标题"
                }
            ],
            "imageWidth": 612,
            "imageHeight": 792
        }
    }
    """
    try:
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        root_temp = Path('temp')
        temp_folders = [temp_folder, root_temp]
        
        ppstructure_data = None
        image_width = 612  # 默认 Letter 尺寸
        image_height = 792
        
        # 查找 ppstructure.json 文件
        for tf in temp_folders:
            ppstructure_path = tf / f"{job_id}_ppstructure.json"
            if ppstructure_path.exists():
                with open(ppstructure_path, 'r', encoding='utf-8') as f:
                    ppstructure_data = json.load(f)
                logger.info(f"Found ppstructure.json at: {ppstructure_path}")
                break
        
        # 尝试获取图像尺寸
        for tf in temp_folders:
            image_path = tf / f"{job_id}_page1.png"
            if image_path.exists():
                try:
                    from PIL import Image
                    with Image.open(image_path) as img:
                        image_width, image_height = img.size
                    logger.info(f"Image size: {image_width}x{image_height}")
                except Exception as e:
                    logger.warning(f"Failed to get image size: {e}")
                break
        
        if ppstructure_data is None:
            return jsonify({
                'success': True,
                'data': {
                    'blocks': [],
                    'imageWidth': image_width,
                    'imageHeight': image_height
                },
                'message': 'No ppstructure data found'
            })
        
        # 解析 PPStructure 数据为标准化的 Block 格式
        blocks = _parse_ppstructure_to_blocks(ppstructure_data)
        
        return jsonify({
            'success': True,
            'data': {
                'blocks': blocks,
                'imageWidth': image_width,
                'imageHeight': image_height
            }
        })
        
    except Exception as e:
        logger.error(f"Get layout with anchors error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _parse_ppstructure_to_blocks(ppstructure_data):
    """
    将 PPStructure 输出解析为标准化的 Block 格式
    
    Args:
        ppstructure_data: PPStructure 输出的 JSON 数据（可能是列表或字典）
        
    Returns:
        标准化的 Block 列表
    """
    blocks = []
    
    # 处理不同的数据格式
    if isinstance(ppstructure_data, dict):
        items = ppstructure_data.get('items', ppstructure_data.get('res', []))
    elif isinstance(ppstructure_data, list):
        items = ppstructure_data
    else:
        return blocks
    
    # 按 y 坐标排序
    sorted_items = sorted(
        items, 
        key=lambda x: x.get('bbox', [0, 0, 0, 0])[1] if isinstance(x.get('bbox'), list) else 0
    )
    
    for index, item in enumerate(sorted_items):
        block_id = f"block_{str(index + 1).padStart(3, '0')}" if hasattr(str, 'padStart') else f"block_{str(index + 1).zfill(3)}"
        
        # 提取 bbox
        bbox = item.get('bbox', [0, 0, 0, 0])
        if isinstance(bbox, list) and len(bbox) >= 4:
            x, y, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            width = x2 - x
            height = y2 - y
        else:
            x, y, width, height = 0, 0, 0, 0
        
        # 提取类型
        block_type = _map_block_type(item.get('type', 'text'))
        
        # 提取置信度
        confidence = item.get('score', item.get('confidence', 0.9))
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except:
                confidence = 0.9
        
        # 提取文本
        text = _extract_block_text(item.get('res', item.get('text', '')))
        
        blocks.append({
            'id': block_id,
            'type': block_type,
            'bbox': {
                'x': int(x),
                'y': int(y),
                'width': int(width),
                'height': int(height)
            },
            'confidence': round(confidence, 4),
            'pageNum': 1,
            'text': text
        })
    
    return blocks


def _map_block_type(raw_type):
    """映射 PPStructure 类型到标准类型"""
    type_map = {
        'text': 'text',
        'title': 'title',
        'doc_title': 'title',
        'table': 'table',
        'figure': 'figure',
        'figure_caption': 'caption',
        'list': 'list',
        'reference': 'reference',
        'header': 'header',
        'footer': 'footer',
        'equation': 'equation'
    }
    return type_map.get(str(raw_type).lower(), 'text')


def _extract_block_text(res):
    """从 res 字段提取文本"""
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
        if 'html' in res:
            # 表格，返回简短描述
            return '[表格]'
    
    return ''


# ============================================================
# Markdown 锚点注入 API
# ============================================================

@api_bp.route('/convert/<job_id>/markdown-with-anchors', methods=['GET'])
def get_markdown_with_anchors(job_id):
    """
    获取带锚点的 Markdown 内容
    
    在 Markdown 生成时注入锚点，锚点格式：
    <div id="block_xxx" data-coords="x,y,w,h" style="display:none;"></div>
    
    Response:
    {
        "success": true,
        "data": {
            "markdown": "<div id=\"block_001\" ...></div>\n# 标题\n...",
            "anchors": [
                { "blockId": "block_001", "position": 0 }
            ]
        }
    }
    """
    try:
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        root_temp = Path('temp')
        temp_folders = [temp_folder, root_temp]
        
        # 首先尝试获取布局数据
        ppstructure_data = None
        for tf in temp_folders:
            ppstructure_path = tf / f"{job_id}_ppstructure.json"
            if ppstructure_path.exists():
                with open(ppstructure_path, 'r', encoding='utf-8') as f:
                    ppstructure_data = json.load(f)
                break
        
        # 尝试获取现有的 Markdown 文件
        existing_markdown = None
        for tf in temp_folders:
            md_path = tf / f"{job_id}_raw_ocr.md"
            if md_path.exists():
                with open(md_path, 'r', encoding='utf-8') as f:
                    existing_markdown = f.read()
                break
        
        # 如果没有现有 Markdown，尝试从 HTML 获取
        if not existing_markdown:
            for tf in temp_folders:
                html_path = tf / f"{job_id}_raw_ocr.html"
                if html_path.exists():
                    with open(html_path, 'r', encoding='utf-8') as f:
                        existing_markdown = f"<!-- HTML Content -->\n{f.read()}"
                    break
        
        # 生成带锚点的 Markdown
        if ppstructure_data:
            markdown_with_anchors, anchors = _generate_markdown_with_anchors(ppstructure_data)
        elif existing_markdown:
            # 如果只有现有 Markdown，返回不带锚点的版本
            markdown_with_anchors = existing_markdown
            anchors = []
        else:
            markdown_with_anchors = "# 无内容\n\n暂无 OCR 识别结果"
            anchors = []
        
        return jsonify({
            'success': True,
            'data': {
                'markdown': markdown_with_anchors,
                'anchors': anchors
            }
        })
        
    except Exception as e:
        logger.error(f"Get markdown with anchors error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _generate_markdown_with_anchors(ppstructure_data):
    """
    从 PPStructure 数据生成带锚点的 Markdown
    
    Args:
        ppstructure_data: PPStructure 输出的 JSON 数据
        
    Returns:
        (markdown_content, anchors_list)
    """
    from bs4 import BeautifulSoup
    
    markdown_parts = []
    anchors = []
    current_position = 0
    
    # 处理不同的数据格式
    if isinstance(ppstructure_data, dict):
        items = ppstructure_data.get('items', ppstructure_data.get('res', []))
    elif isinstance(ppstructure_data, list):
        items = ppstructure_data
    else:
        return "# 无内容\n\n数据格式错误", []
    
    # 按 y 坐标排序
    sorted_items = sorted(
        items,
        key=lambda x: x.get('bbox', [0, 0, 0, 0])[1] if isinstance(x.get('bbox'), list) else 0
    )
    
    for index, item in enumerate(sorted_items):
        block_id = f"block_{str(index + 1).zfill(3)}"
        
        # 提取 bbox
        bbox = item.get('bbox', [0, 0, 0, 0])
        if isinstance(bbox, list) and len(bbox) >= 4:
            x, y, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            width = x2 - x
            height = y2 - y
        else:
            x, y, width, height = 0, 0, 0, 0
        
        # 生成锚点 HTML
        anchor_html = f'<div id="{block_id}" data-coords="{x},{y},{width},{height}" style="display:none;"></div>'
        
        # 记录锚点位置
        anchors.append({
            'blockId': block_id,
            'position': current_position,
            'coords': {'x': x, 'y': y, 'width': width, 'height': height}
        })
        
        # 添加锚点
        markdown_parts.append(anchor_html)
        current_position += len(anchor_html) + 1  # +1 for newline
        
        # 生成内容
        item_type = item.get('type', 'text')
        res = item.get('res', item.get('text', ''))
        content = _generate_block_content(item_type, res)
        
        if content:
            markdown_parts.append(content)
            current_position += len(content) + 1
        
        # 添加空行分隔
        markdown_parts.append('')
        current_position += 1
    
    return '\n'.join(markdown_parts), anchors


def _generate_block_content(item_type, res):
    """根据 Block 类型生成 Markdown 内容"""
    from bs4 import BeautifulSoup
    
    item_type = str(item_type).lower()
    
    if item_type in ('title', 'doc_title'):
        text = _extract_block_text(res)
        return f"# {text}" if text else ""
    
    elif item_type == 'text':
        text = _extract_block_text(res)
        return text if text else ""
    
    elif item_type in ('header', 'footer'):
        text = _extract_block_text(res)
        return f"*{text}*" if text else ""
    
    elif item_type == 'table':
        if isinstance(res, dict) and 'html' in res:
            return _html_table_to_markdown(res['html'])
        return "[表格]"
    
    elif item_type == 'figure_caption':
        text = _extract_block_text(res)
        return f"**{text}**" if text else ""
    
    elif item_type == 'reference':
        text = _extract_block_text(res)
        return f"*{text}*" if text else ""
    
    elif item_type == 'equation':
        text = _extract_block_text(res)
        return f"${text}$" if text else ""
    
    elif item_type == 'figure':
        return "*[图片]*"
    
    elif item_type == 'list':
        text = _extract_block_text(res)
        if text:
            # 尝试将文本转换为列表格式
            lines = text.split('\n')
            return '\n'.join(f"- {line.strip()}" for line in lines if line.strip())
        return ""
    
    else:
        text = _extract_block_text(res)
        return text if text else ""


def _html_table_to_markdown(html_content):
    """HTML 表格转 Markdown"""
    from bs4 import BeautifulSoup
    
    if not html_content:
        return "[空表格]"
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table')
        
        if not table:
            return "[表格解析失败]"
        
        rows = table.find_all('tr')
        markdown_rows = []
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            cell_texts = [cell.get_text(strip=True).replace('|', '\\|').replace('\n', ' ') for cell in cells]
            
            if not cell_texts:
                continue
            
            markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
            
            # 第一行后添加分隔符
            if row_idx == 0:
                separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
                markdown_rows.append(separator)
        
        return '\n'.join(markdown_rows) if markdown_rows else "[空表格]"
    except Exception as e:
        logger.warning(f"Failed to convert HTML table to Markdown: {e}")
        return "[表格转换失败]"


# ============================================================
# 内容保存 API
# ============================================================

@api_bp.route('/convert/<job_id>/save-markdown', methods=['POST'])
def save_markdown(job_id):
    """
    保存修正后的 Markdown 内容
    
    Request:
    {
        "markdown": "修正后的 Markdown 内容...",
        "updateVector": true  // 是否更新向量库（可选）
    }
    
    Response:
    {
        "success": true,
        "data": {
            "savedAt": "2026-01-28T10:30:00Z",
            "vectorUpdated": true,
            "filePath": "temp/xxx_corrected.md"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '无效的请求数据'
            }), 400
        
        markdown_content = data.get('markdown', '')
        update_vector = data.get('updateVector', False)
        
        if not markdown_content:
            return jsonify({
                'success': False,
                'error': 'Markdown 内容不能为空'
            }), 400
        
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        if not isinstance(temp_folder, Path):
            temp_folder = Path(temp_folder)
        temp_folder.mkdir(exist_ok=True)
        
        # 保存修正后的 Markdown
        corrected_path = temp_folder / f"{job_id}_corrected.md"
        with open(corrected_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Saved corrected Markdown for job {job_id} to {corrected_path}")
        
        # 可选：更新向量库
        vector_updated = False
        if update_vector:
            try:
                vector_updated = _update_vector_store(job_id, markdown_content)
            except Exception as e:
                logger.warning(f"Failed to update vector store: {e}")
        
        saved_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        return jsonify({
            'success': True,
            'data': {
                'savedAt': saved_at,
                'vectorUpdated': vector_updated,
                'filePath': str(corrected_path)
            }
        })
        
    except Exception as e:
        logger.error(f"Save markdown error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _update_vector_store(job_id, markdown_content):
    """
    更新向量库中的文档内容
    
    Args:
        job_id: 任务 ID
        markdown_content: 修正后的 Markdown 内容
        
    Returns:
        是否更新成功
    """
    try:
        # 尝试导入向量存储服务
        from backend.services.vector_store import get_vector_store
        
        vector_store = get_vector_store()
        if vector_store is None:
            logger.warning("Vector store not initialized")
            return False
        
        # 删除旧的文档向量
        vector_store.delete_document(job_id)
        
        # 添加新的文档向量
        from backend.services.text_chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text(markdown_content)
        
        for i, chunk in enumerate(chunks):
            vector_store.add_document(
                doc_id=f"{job_id}_chunk_{i}",
                content=chunk,
                metadata={'job_id': job_id, 'chunk_index': i}
            )
        
        logger.info(f"Updated vector store for job {job_id} with {len(chunks)} chunks")
        return True
        
    except ImportError:
        logger.warning("Vector store module not available")
        return False
    except Exception as e:
        logger.error(f"Failed to update vector store: {e}")
        return False
