"""
单据类型配置 API 路由
提供单据类型的 CRUD 操作
"""

from flask import Blueprint, request, jsonify
import json
import os
from datetime import datetime

document_type_bp = Blueprint('document_type', __name__)

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'document_types.json')

# 默认单据类型配置
DEFAULT_DOCUMENT_TYPES = [
    {
        "id": "invoice",
        "name": "发票",
        "fields": ["发票号码", "发票代码", "开票日期", "购买方名称", "销售方名称", "金额", "税额", "价税合计"],
        "checkpoints": [
            "发票号码是多少？",
            "开票日期是什么？",
            "金额合计是多少？",
            "购买方名称是什么？"
        ],
        "is_default": True
    },
    {
        "id": "contract",
        "name": "合同",
        "fields": ["合同编号", "甲方", "乙方", "签订日期", "合同金额", "有效期"],
        "checkpoints": [
            "合同编号是多少？",
            "甲方和乙方分别是谁？",
            "合同金额是多少？",
            "签订日期是什么？"
        ],
        "is_default": True
    },
    {
        "id": "receipt",
        "name": "收据",
        "fields": ["收据编号", "日期", "付款人", "收款人", "金额", "事由"],
        "checkpoints": [
            "收据编号是多少？",
            "金额是多少？",
            "付款人和收款人分别是谁？"
        ],
        "is_default": True
    },
    {
        "id": "id_card",
        "name": "身份证",
        "fields": ["姓名", "性别", "民族", "出生日期", "住址", "身份证号码"],
        "checkpoints": [
            "姓名是什么？",
            "身份证号码是多少？",
            "出生日期是什么？"
        ],
        "is_default": True
    },
    {
        "id": "trip_report",
        "name": "出差报告",
        "fields": ["报告日期", "出差人", "出差目的地", "出差事由", "出差时间", "费用合计"],
        "checkpoints": [
            "出差人是谁？",
            "出差目的地是哪里？",
            "费用合计是多少？"
        ],
        "is_default": True
    }
]


def load_document_types():
    """加载单据类型配置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading document types: {e}")
    
    # 返回默认配置
    return DEFAULT_DOCUMENT_TYPES.copy()


def save_document_types(document_types):
    """保存单据类型配置"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(document_types, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving document types: {e}")
        return False


@document_type_bp.route('/api/document-types', methods=['GET'])
def get_document_types():
    """获取所有单据类型配置"""
    try:
        document_types = load_document_types()
        return jsonify({
            "success": True,
            "data": document_types
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@document_type_bp.route('/api/document-types/<type_id>', methods=['GET'])
def get_document_type(type_id):
    """获取单个单据类型配置"""
    try:
        document_types = load_document_types()
        doc_type = next((t for t in document_types if t['id'] == type_id), None)
        
        if not doc_type:
            return jsonify({
                "success": False,
                "error": f"单据类型 '{type_id}' 不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "data": doc_type
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@document_type_bp.route('/api/document-types', methods=['POST'])
def create_document_type():
    """创建新单据类型"""
    try:
        data = request.get_json()
        
        if not data.get('id') or not data.get('name'):
            return jsonify({
                "success": False,
                "error": "缺少必填字段: id, name"
            }), 400
        
        document_types = load_document_types()
        
        # 检查 ID 是否已存在
        if any(t['id'] == data['id'] for t in document_types):
            return jsonify({
                "success": False,
                "error": f"单据类型 ID '{data['id']}' 已存在"
            }), 400
        
        new_type = {
            "id": data['id'],
            "name": data['name'],
            "fields": data.get('fields', []),
            "checkpoints": data.get('checkpoints', []),
            "is_default": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        document_types.append(new_type)
        
        if save_document_types(document_types):
            return jsonify({
                "success": True,
                "data": new_type
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "保存失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@document_type_bp.route('/api/document-types/<type_id>', methods=['PUT'])
def update_document_type(type_id):
    """更新单据类型"""
    try:
        data = request.get_json()
        document_types = load_document_types()
        
        # 查找要更新的类型
        type_index = next((i for i, t in enumerate(document_types) if t['id'] == type_id), None)
        
        if type_index is None:
            return jsonify({
                "success": False,
                "error": f"单据类型 '{type_id}' 不存在"
            }), 404
        
        # 更新字段
        doc_type = document_types[type_index]
        if 'name' in data:
            doc_type['name'] = data['name']
        if 'fields' in data:
            doc_type['fields'] = data['fields']
        if 'checkpoints' in data:
            doc_type['checkpoints'] = data['checkpoints']
        doc_type['updated_at'] = datetime.now().isoformat()
        
        if save_document_types(document_types):
            return jsonify({
                "success": True,
                "data": doc_type
            })
        else:
            return jsonify({
                "success": False,
                "error": "保存失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@document_type_bp.route('/api/document-types/<type_id>', methods=['DELETE'])
def delete_document_type(type_id):
    """删除单据类型"""
    try:
        document_types = load_document_types()
        
        # 查找要删除的类型
        type_index = next((i for i, t in enumerate(document_types) if t['id'] == type_id), None)
        
        if type_index is None:
            return jsonify({
                "success": False,
                "error": f"单据类型 '{type_id}' 不存在"
            }), 404
        
        # 检查是否为默认类型
        if document_types[type_index].get('is_default'):
            return jsonify({
                "success": False,
                "error": "不能删除默认单据类型"
            }), 400
        
        deleted_type = document_types.pop(type_index)
        
        if save_document_types(document_types):
            return jsonify({
                "success": True,
                "message": f"已删除单据类型 '{deleted_type['name']}'"
            })
        else:
            return jsonify({
                "success": False,
                "error": "保存失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@document_type_bp.route('/api/document-types/reset', methods=['POST'])
def reset_document_types():
    """重置为默认单据类型配置"""
    try:
        if save_document_types(DEFAULT_DOCUMENT_TYPES.copy()):
            return jsonify({
                "success": True,
                "message": "已重置为默认配置",
                "data": DEFAULT_DOCUMENT_TYPES
            })
        else:
            return jsonify({
                "success": False,
                "error": "重置失败"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
