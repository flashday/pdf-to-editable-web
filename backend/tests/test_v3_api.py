"""
V3 API 测试
测试修正记录、检查点、最终结果和模板管理 API
"""
import pytest
import json
import tempfile
from pathlib import Path


class TestCorrectionsAPI:
    """修正记录 API 测试"""
    
    def test_save_correction_success(self, client, app):
        """测试保存修正记录"""
        job_id = 'test-job-001'
        correction_data = {
            'blockIndex': 0,
            'originalText': '原始文本',
            'correctedText': '修正后文本',
            'tableHtml': None
        }
        
        response = client.post(
            f'/api/corrections/{job_id}',
            json=correction_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['correction']['blockIndex'] == 0
        assert data['correction']['correctedText'] == '修正后文本'
    
    def test_save_correction_update_existing(self, client, app):
        """测试更新已存在的修正记录"""
        job_id = 'test-job-002'
        
        # 第一次保存
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '第一次修正'},
            content_type='application/json'
        )
        
        # 第二次保存同一 block
        response = client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '第二次修正'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # 获取并验证只有一条记录
        get_response = client.get(f'/api/corrections/{job_id}')
        data = get_response.get_json()
        assert data['count'] == 1
        assert data['corrections'][0]['correctedText'] == '第二次修正'
    
    def test_save_correction_invalid_data(self, client):
        """测试无效数据"""
        response = client.post(
            '/api/corrections/test-job',
            data='invalid',
            content_type='application/json'
        )
        
        # Flask 解析无效 JSON 时返回 500 或 400
        assert response.status_code in [400, 500]
    
    def test_get_corrections_empty(self, client):
        """测试获取空修正记录"""
        response = client.get('/api/corrections/nonexistent-job')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['corrections'] == []
        assert data['count'] == 0
    
    def test_get_corrections_with_data(self, client, app):
        """测试获取有数据的修正记录"""
        job_id = 'test-job-003'
        
        # 保存多条修正
        for i in range(3):
            client.post(
                f'/api/corrections/{job_id}',
                json={'blockIndex': i, 'correctedText': f'修正 {i}'},
                content_type='application/json'
            )
        
        response = client.get(f'/api/corrections/{job_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 3


class TestCheckpointsAPI:
    """检查点 API 测试"""
    
    def test_save_checkpoints_success(self, client, app):
        """测试保存检查点结果"""
        job_id = 'test-job-cp-001'
        checkpoint_data = {
            'results': [
                {'question': '金额是多少？', 'answer': '10000元'},
                {'question': '日期是什么？', 'answer': '2024-01-15'}
            ],
            'executed_at': '2024-01-15T10:00:00Z'
        }
        
        response = client.post(
            f'/api/checkpoints/{job_id}',
            json=checkpoint_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']['results']) == 2
    
    def test_save_checkpoints_invalid_data(self, client):
        """测试无效数据"""
        response = client.post(
            '/api/checkpoints/test-job',
            data='invalid',
            content_type='application/json'
        )
        
        # Flask 解析无效 JSON 时返回 500 或 400
        assert response.status_code in [400, 500]
    
    def test_get_checkpoints_empty(self, client):
        """测试获取空检查点结果"""
        response = client.get('/api/checkpoints/nonexistent-job')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] is None
    
    def test_get_checkpoints_with_data(self, client, app):
        """测试获取有数据的检查点结果"""
        job_id = 'test-job-cp-002'
        
        # 先保存
        client.post(
            f'/api/checkpoints/{job_id}',
            json={'results': [{'question': 'Q1', 'answer': 'A1'}]},
            content_type='application/json'
        )
        
        response = client.get(f'/api/checkpoints/{job_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] is not None
        assert len(data['data']['results']) == 1


class TestFinalResultAPI:
    """最终结果 API 测试"""
    
    def test_save_final_result_success(self, client, app):
        """测试保存最终结果"""
        job_id = 'test-job-final-001'
        final_data = {
            'filename': 'test.pdf',
            'extractedData': {'company': '测试公司', 'amount': 10000},
            'checkpointResults': [{'question': 'Q1', 'answer': 'A1'}],
            'corrections': [],
            'status': 'confirmed'
        }
        
        response = client.post(
            f'/api/final/{job_id}',
            json=final_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'confirmed'
    
    def test_save_final_result_rejected(self, client, app):
        """测试保存驳回结果"""
        job_id = 'test-job-final-002'
        
        response = client.post(
            f'/api/final/{job_id}',
            json={'status': 'rejected', 'extractedData': {}},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['status'] == 'rejected'
    
    def test_get_final_result_empty(self, client):
        """测试获取空最终结果"""
        response = client.get('/api/final/nonexistent-job')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] is None
    
    def test_get_final_result_with_data(self, client, app):
        """测试获取有数据的最终结果"""
        job_id = 'test-job-final-003'
        
        # 先保存
        client.post(
            f'/api/final/{job_id}',
            json={'extractedData': {'key': 'value'}, 'status': 'confirmed'},
            content_type='application/json'
        )
        
        response = client.get(f'/api/final/{job_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] is not None
        assert data['data']['extractedData']['key'] == 'value'


class TestTemplatesAPI:
    """模板管理 API 测试"""
    
    def test_get_templates_empty(self, client, app):
        """测试获取空模板列表"""
        response = client.get('/api/templates')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert isinstance(data['templates'], list)
    
    def test_create_template_success(self, client, app):
        """测试创建模板"""
        template_data = {
            'name': '测试模板',
            'fields': ['公司名称', '金额', '日期']
        }
        
        response = client.post(
            '/api/templates',
            json=template_data,
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['template']['name'] == '测试模板'
        assert 'id' in data['template']
        assert data['template']['isPreset'] is False
    
    def test_create_template_no_name(self, client):
        """测试创建无名称模板"""
        response = client.post(
            '/api/templates',
            json={'fields': ['field1']},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_update_template_success(self, client, app):
        """测试更新模板"""
        # 先创建
        create_response = client.post(
            '/api/templates',
            json={'name': '原始名称', 'fields': ['field1']},
            content_type='application/json'
        )
        template_id = create_response.get_json()['template']['id']
        
        # 更新
        response = client.put(
            f'/api/templates/{template_id}',
            json={'name': '新名称', 'fields': ['field1', 'field2']},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['template']['name'] == '新名称'
        assert len(data['template']['fields']) == 2
    
    def test_update_template_not_found(self, client):
        """测试更新不存在的模板"""
        response = client.put(
            '/api/templates/nonexistent-id',
            json={'name': 'test'},
            content_type='application/json'
        )
        
        assert response.status_code == 404
    
    def test_delete_template_success(self, client, app):
        """测试删除模板"""
        # 先创建
        create_response = client.post(
            '/api/templates',
            json={'name': '待删除模板', 'fields': []},
            content_type='application/json'
        )
        template_id = create_response.get_json()['template']['id']
        
        # 删除
        response = client.delete(f'/api/templates/{template_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_delete_template_not_found(self, client):
        """测试删除不存在的模板"""
        response = client.delete('/api/templates/nonexistent-id')
        
        assert response.status_code == 404


class TestCheckpointConfigAPI:
    """检查点配置 API 测试"""
    
    def test_get_checkpoint_config_default(self, client, app):
        """测试获取默认检查点配置"""
        response = client.get('/api/checkpoint-config')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'checkpoints' in data
        assert isinstance(data['checkpoints'], list)
    
    def test_save_checkpoint_config_success(self, client, app):
        """测试保存检查点配置"""
        config_data = {
            'checkpoints': [
                {'id': 'cp1', 'question': '自定义问题1', 'enabled': True},
                {'id': 'cp2', 'question': '自定义问题2', 'enabled': False}
            ]
        }
        
        response = client.post(
            '/api/checkpoint-config',
            json=config_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['checkpoints']) == 2
    
    def test_save_checkpoint_config_invalid_data(self, client):
        """测试无效数据"""
        response = client.post(
            '/api/checkpoint-config',
            data='invalid',
            content_type='application/json'
        )
        
        # Flask 解析无效 JSON 时返回 500 或 400
        assert response.status_code in [400, 500]
    
    def test_checkpoint_config_persistence(self, client, app):
        """测试检查点配置持久化"""
        # 保存配置
        client.post(
            '/api/checkpoint-config',
            json={'checkpoints': [{'id': 'test', 'question': '测试问题', 'enabled': True}]},
            content_type='application/json'
        )
        
        # 重新获取
        response = client.get('/api/checkpoint-config')
        data = response.get_json()
        
        assert any(cp['id'] == 'test' for cp in data['checkpoints'])
