"""
V3 升级 API 路由
处理修正记录、检查点、最终结果和模板管理
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
# 修正记录 API
# ============================================================

@api_bp.route('/corrections/<job_id>', methods=['POST'])
def save_correction(job_id):
    """保存修正记录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        corrections_file = temp_folder / f"{job_id}_corrections.json"
        
        # 加载现有修正记录
        corrections = []
        if corrections_file.exists():
            with open(corrections_file, 'r', encoding='utf-8') as f:
                corrections = json.load(f)
        
        # 查找是否已有该 block 的修正
        block_index = data.get('blockIndex')
        existing_idx = None
        for i, c in enumerate(corrections):
            if c.get('blockIndex') == block_index:
                existing_idx = i
                break
        
        # 更新或添加修正
        correction_record = {
            'blockIndex': block_index,
            'originalText': data.get('originalText', ''),
            'correctedText': data.get('correctedText', ''),
            'tableHtml': data.get('tableHtml'),
            'timestamp': data.get('timestamp', time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        }
        
        if existing_idx is not None:
            corrections[existing_idx] = correction_record
        else:
            corrections.append(correction_record)
        
        # 保存到文件
        with open(corrections_file, 'w', encoding='utf-8') as f:
            json.dump(corrections, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved correction for job {job_id}, block {block_index}")
        
        return jsonify({
            'success': True,
            'message': '修正已保存',
            'correction': correction_record
        })
        
    except Exception as e:
        logger.error(f"Save correction error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/corrections/<job_id>', methods=['GET'])
def get_corrections(job_id):
    """获取修正记录"""
    try:
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        corrections_file = temp_folder / f"{job_id}_corrections.json"
        
        if not corrections_file.exists():
            return jsonify({
                'success': True,
                'corrections': [],
                'count': 0
            })
        
        with open(corrections_file, 'r', encoding='utf-8') as f:
            corrections = json.load(f)
        
        return jsonify({
            'success': True,
            'corrections': corrections,
            'count': len(corrections)
        })
        
    except Exception as e:
        logger.error(f"Get corrections error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 检查点 API
# ============================================================

@api_bp.route('/checkpoints/<job_id>', methods=['POST'])
def save_checkpoints(job_id):
    """保存检查点结果"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        checkpoints_file = temp_folder / f"{job_id}_checkpoints.json"
        
        checkpoint_data = {
            'job_id': job_id,
            'results': data.get('results', []),
            'executed_at': data.get('executed_at', time.strftime('%Y-%m-%dT%H:%M:%SZ')),
            'saved_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        with open(checkpoints_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved checkpoints for job {job_id}")
        
        return jsonify({
            'success': True,
            'message': '检查点结果已保存',
            'data': checkpoint_data
        })
        
    except Exception as e:
        logger.error(f"Save checkpoints error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/checkpoints/<job_id>', methods=['GET'])
def get_checkpoints(job_id):
    """获取检查点结果"""
    try:
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        checkpoints_file = temp_folder / f"{job_id}_checkpoints.json"
        
        if not checkpoints_file.exists():
            return jsonify({
                'success': True,
                'data': None,
                'message': '暂无检查点结果'
            })
        
        with open(checkpoints_file, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': checkpoint_data
        })
        
    except Exception as e:
        logger.error(f"Get checkpoints error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 最终结果 API
# ============================================================

@api_bp.route('/final/<job_id>', methods=['POST'])
def save_final_result(job_id):
    """保存最终确认结果"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        final_file = temp_folder / f"{job_id}_final_result.json"
        
        final_data = {
            'job_id': job_id,
            'filename': data.get('filename'),
            'extractedData': data.get('extractedData', {}),
            'checkpointResults': data.get('checkpointResults', []),
            'corrections': data.get('corrections', []),
            'status': data.get('status', 'confirmed'),
            'confirmedAt': data.get('confirmedAt', time.strftime('%Y-%m-%dT%H:%M:%SZ')),
            'savedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved final result for job {job_id}")
        
        return jsonify({
            'success': True,
            'message': '最终结果已保存',
            'data': final_data
        })
        
    except Exception as e:
        logger.error(f"Save final result error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/final/<job_id>', methods=['GET'])
def get_final_result(job_id):
    """获取最终确认结果"""
    try:
        temp_folder = current_app.config.get('TEMP_FOLDER', Path('temp'))
        final_file = temp_folder / f"{job_id}_final_result.json"
        
        if not final_file.exists():
            return jsonify({
                'success': True,
                'data': None,
                'message': '暂无最终结果'
            })
        
        with open(final_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': final_data
        })
        
    except Exception as e:
        logger.error(f"Get final result error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 模板管理 API
# ============================================================

# 模板存储文件
TEMPLATES_FILE = 'templates.json'

def get_templates_path():
    """获取模板存储路径"""
    config_folder = current_app.config.get('CONFIG_FOLDER', Path('config'))
    if not isinstance(config_folder, Path):
        config_folder = Path(config_folder)
    config_folder.mkdir(exist_ok=True)
    return config_folder / TEMPLATES_FILE


def load_templates():
    """加载模板"""
    templates_path = get_templates_path()
    if templates_path.exists():
        with open(templates_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_templates(templates):
    """保存模板"""
    templates_path = get_templates_path()
    with open(templates_path, 'w', encoding='utf-8') as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


@api_bp.route('/templates', methods=['GET'])
def get_templates():
    """获取所有模板"""
    try:
        templates = load_templates()
        return jsonify({
            'success': True,
            'templates': templates,
            'count': len(templates)
        })
    except Exception as e:
        logger.error(f"Get templates error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/templates', methods=['POST'])
def create_template():
    """创建新模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        name = data.get('name')
        fields = data.get('fields', [])
        
        if not name:
            return jsonify({'success': False, 'error': '模板名称不能为空'}), 400
        
        templates = load_templates()
        
        # 生成唯一 ID
        template_id = f"tpl_{int(time.time() * 1000)}"
        
        new_template = {
            'id': template_id,
            'name': name,
            'fields': fields,
            'isPreset': False,
            'createdAt': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        templates.append(new_template)
        save_templates(templates)
        
        logger.info(f"Created template: {template_id}")
        
        return jsonify({
            'success': True,
            'message': '模板已创建',
            'template': new_template
        }), 201
        
    except Exception as e:
        logger.error(f"Create template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    """更新模板"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        templates = load_templates()
        
        # 查找模板
        template_idx = None
        for i, t in enumerate(templates):
            if t.get('id') == template_id:
                template_idx = i
                break
        
        if template_idx is None:
            return jsonify({'success': False, 'error': '模板不存在'}), 404
        
        # 不允许修改预设模板
        if templates[template_idx].get('isPreset'):
            return jsonify({'success': False, 'error': '不能修改预设模板'}), 403
        
        # 更新模板
        templates[template_idx]['name'] = data.get('name', templates[template_idx]['name'])
        templates[template_idx]['fields'] = data.get('fields', templates[template_idx]['fields'])
        templates[template_idx]['updatedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        save_templates(templates)
        
        logger.info(f"Updated template: {template_id}")
        
        return jsonify({
            'success': True,
            'message': '模板已更新',
            'template': templates[template_idx]
        })
        
    except Exception as e:
        logger.error(f"Update template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """删除模板"""
    try:
        templates = load_templates()
        
        # 查找模板
        template_idx = None
        for i, t in enumerate(templates):
            if t.get('id') == template_id:
                template_idx = i
                break
        
        if template_idx is None:
            return jsonify({'success': False, 'error': '模板不存在'}), 404
        
        # 不允许删除预设模板
        if templates[template_idx].get('isPreset'):
            return jsonify({'success': False, 'error': '不能删除预设模板'}), 403
        
        # 删除模板
        deleted = templates.pop(template_idx)
        save_templates(templates)
        
        logger.info(f"Deleted template: {template_id}")
        
        return jsonify({
            'success': True,
            'message': '模板已删除',
            'template': deleted
        })
        
    except Exception as e:
        logger.error(f"Delete template error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 检查点配置 API
# ============================================================

CHECKPOINT_CONFIG_FILE = 'checkpoint_config.json'

def get_checkpoint_config_path():
    """获取检查点配置路径"""
    config_folder = current_app.config.get('CONFIG_FOLDER', Path('config'))
    if not isinstance(config_folder, Path):
        config_folder = Path(config_folder)
    config_folder.mkdir(exist_ok=True)
    return config_folder / CHECKPOINT_CONFIG_FILE


def load_checkpoint_config():
    """加载检查点配置"""
    config_path = get_checkpoint_config_path()
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 默认配置
    return {
        'checkpoints': [
            {'id': 'cp1', 'question': '文档中的主要金额是多少？', 'enabled': True},
            {'id': 'cp2', 'question': '文档的日期是什么？', 'enabled': True},
            {'id': 'cp3', 'question': '文档涉及的主要当事方有哪些？', 'enabled': True}
        ]
    }


def save_checkpoint_config(config):
    """保存检查点配置"""
    config_path = get_checkpoint_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@api_bp.route('/checkpoint-config', methods=['GET'])
def get_checkpoint_config():
    """获取检查点配置"""
    try:
        config = load_checkpoint_config()
        return jsonify({
            'success': True,
            'checkpoints': config.get('checkpoints', [])
        })
    except Exception as e:
        logger.error(f"Get checkpoint config error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/checkpoint-config', methods=['POST'])
def save_checkpoint_config_api():
    """保存检查点配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        checkpoints = data.get('checkpoints', [])
        
        config = {
            'checkpoints': checkpoints,
            'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        save_checkpoint_config(config)
        
        logger.info("Saved checkpoint config")
        
        return jsonify({
            'success': True,
            'message': '检查点配置已保存',
            'checkpoints': checkpoints
        })
        
    except Exception as e:
        logger.error(f"Save checkpoint config error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
