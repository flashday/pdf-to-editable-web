"""
V3 集成测试
测试完整工作流、修正数据传递、驳回流程和数据持久化
"""
import pytest
import json
import time
from pathlib import Path


class TestWorkflowIntegration:
    """完整工作流集成测试（步骤 1-6）"""
    
    def test_complete_workflow_simulation(self, client, app):
        """模拟完整工作流程"""
        job_id = f'workflow-test-{int(time.time())}'
        
        # 步骤 1-3: 模拟 OCR 完成（通过直接设置状态）
        # 实际场景中这些步骤由 OCR 服务完成
        
        # 步骤 4: 保存修正记录
        corrections = [
            {'blockIndex': 0, 'originalText': '原文1', 'correctedText': '修正1'},
            {'blockIndex': 2, 'originalText': '原文3', 'correctedText': '修正3'}
        ]
        
        for correction in corrections:
            response = client.post(
                f'/api/corrections/{job_id}',
                json=correction,
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # 验证修正记录
        corrections_response = client.get(f'/api/corrections/{job_id}')
        assert corrections_response.get_json()['count'] == 2
        
        # 步骤 5: 保存检查点结果
        checkpoint_data = {
            'results': [
                {'question': '文档金额', 'answer': '50000元'},
                {'question': '签署日期', 'answer': '2024-01-20'}
            ]
        }
        
        response = client.post(
            f'/api/checkpoints/{job_id}',
            json=checkpoint_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 步骤 6: 保存最终确认结果
        final_data = {
            'filename': 'test_document.pdf',
            'extractedData': {
                'company': '测试有限公司',
                'amount': 50000,
                'date': '2024-01-20'
            },
            'checkpointResults': checkpoint_data['results'],
            'corrections': corrections,
            'status': 'confirmed'
        }
        
        response = client.post(
            f'/api/final/{job_id}',
            json=final_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # 验证最终结果
        final_response = client.get(f'/api/final/{job_id}')
        final_result = final_response.get_json()['data']
        
        assert final_result['status'] == 'confirmed'
        assert final_result['extractedData']['company'] == '测试有限公司'
        assert len(final_result['corrections']) == 2


class TestCorrectionDataFlow:
    """修正数据传递测试（步骤 4→5）"""
    
    def test_corrections_available_for_extraction(self, client, app):
        """测试修正数据在提取阶段可用"""
        job_id = f'correction-flow-{int(time.time())}'
        
        # 步骤 4: 保存修正
        corrections = [
            {'blockIndex': 0, 'originalText': '错误文本', 'correctedText': '正确文本'},
            {'blockIndex': 1, 'originalText': '表格数据', 'correctedText': '修正表格', 
             'tableHtml': '<table><tr><td>修正</td></tr></table>'}
        ]
        
        for c in corrections:
            client.post(f'/api/corrections/{job_id}', json=c, content_type='application/json')
        
        # 步骤 5: 获取修正数据用于提取
        response = client.get(f'/api/corrections/{job_id}')
        data = response.get_json()
        
        assert data['success'] is True
        assert data['count'] == 2
        
        # 验证修正内容完整
        correction_map = {c['blockIndex']: c for c in data['corrections']}
        assert correction_map[0]['correctedText'] == '正确文本'
        assert correction_map[1]['tableHtml'] is not None
    
    def test_corrections_merge_with_original(self, client, app):
        """测试修正与原始数据合并"""
        job_id = f'merge-test-{int(time.time())}'
        
        # 只修正部分 block
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 1, 'originalText': 'B', 'correctedText': 'B-fixed'},
            content_type='application/json'
        )
        
        # 获取修正
        response = client.get(f'/api/corrections/{job_id}')
        corrections = response.get_json()['corrections']
        
        # 应该只有一条修正记录
        assert len(corrections) == 1
        assert corrections[0]['blockIndex'] == 1


class TestRejectionFlow:
    """驳回流程测试（步骤 6→4）"""
    
    def test_rejection_preserves_data(self, client, app):
        """测试驳回后数据保留"""
        job_id = f'rejection-test-{int(time.time())}'
        
        # 步骤 4: 初始修正
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '初始修正'},
            content_type='application/json'
        )
        
        # 步骤 5: 检查点
        client.post(
            f'/api/checkpoints/{job_id}',
            json={'results': [{'question': 'Q', 'answer': 'A'}]},
            content_type='application/json'
        )
        
        # 步骤 6: 驳回
        client.post(
            f'/api/final/{job_id}',
            json={'status': 'rejected', 'extractedData': {}},
            content_type='application/json'
        )
        
        # 验证修正数据仍然存在
        corrections_response = client.get(f'/api/corrections/{job_id}')
        assert corrections_response.get_json()['count'] == 1
        
        # 验证检查点数据仍然存在
        checkpoints_response = client.get(f'/api/checkpoints/{job_id}')
        assert checkpoints_response.get_json()['data'] is not None
    
    def test_rejection_allows_re_correction(self, client, app):
        """测试驳回后可以重新修正"""
        job_id = f'recorrection-test-{int(time.time())}'
        
        # 初始修正
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '第一次修正'},
            content_type='application/json'
        )
        
        # 驳回
        client.post(
            f'/api/final/{job_id}',
            json={'status': 'rejected', 'extractedData': {}},
            content_type='application/json'
        )
        
        # 重新修正
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '第二次修正'},
            content_type='application/json'
        )
        
        # 验证修正已更新
        response = client.get(f'/api/corrections/{job_id}')
        corrections = response.get_json()['corrections']
        
        assert len(corrections) == 1
        assert corrections[0]['correctedText'] == '第二次修正'
    
    def test_multiple_rejections(self, client, app):
        """测试多次驳回"""
        job_id = f'multi-reject-{int(time.time())}'
        
        for i in range(3):
            # 修正
            client.post(
                f'/api/corrections/{job_id}',
                json={'blockIndex': 0, 'correctedText': f'修正 {i}'},
                content_type='application/json'
            )
            
            # 驳回
            client.post(
                f'/api/final/{job_id}',
                json={'status': 'rejected', 'extractedData': {}},
                content_type='application/json'
            )
        
        # 最终确认
        client.post(
            f'/api/final/{job_id}',
            json={'status': 'confirmed', 'extractedData': {'final': True}},
            content_type='application/json'
        )
        
        # 验证最终状态
        response = client.get(f'/api/final/{job_id}')
        assert response.get_json()['data']['status'] == 'confirmed'


class TestDataPersistence:
    """数据持久化测试"""
    
    def test_corrections_persist_across_requests(self, client, app):
        """测试修正数据跨请求持久化"""
        job_id = f'persist-corrections-{int(time.time())}'
        
        # 保存
        client.post(
            f'/api/corrections/{job_id}',
            json={'blockIndex': 0, 'correctedText': '持久化测试'},
            content_type='application/json'
        )
        
        # 多次获取验证
        for _ in range(3):
            response = client.get(f'/api/corrections/{job_id}')
            assert response.get_json()['count'] == 1
    
    def test_checkpoints_persist_across_requests(self, client, app):
        """测试检查点数据跨请求持久化"""
        job_id = f'persist-checkpoints-{int(time.time())}'
        
        # 保存
        client.post(
            f'/api/checkpoints/{job_id}',
            json={'results': [{'question': 'Q', 'answer': 'A'}]},
            content_type='application/json'
        )
        
        # 多次获取验证
        for _ in range(3):
            response = client.get(f'/api/checkpoints/{job_id}')
            assert response.get_json()['data'] is not None
    
    def test_final_result_persist_across_requests(self, client, app):
        """测试最终结果跨请求持久化"""
        job_id = f'persist-final-{int(time.time())}'
        
        # 保存
        client.post(
            f'/api/final/{job_id}',
            json={'status': 'confirmed', 'extractedData': {'key': 'value'}},
            content_type='application/json'
        )
        
        # 多次获取验证
        for _ in range(3):
            response = client.get(f'/api/final/{job_id}')
            data = response.get_json()['data']
            assert data['status'] == 'confirmed'
            assert data['extractedData']['key'] == 'value'
    
    def test_templates_persist_across_requests(self, client, app):
        """测试模板数据跨请求持久化"""
        # 创建模板
        create_response = client.post(
            '/api/templates',
            json={'name': '持久化模板', 'fields': ['field1']},
            content_type='application/json'
        )
        template_id = create_response.get_json()['template']['id']
        
        # 多次获取验证
        for _ in range(3):
            response = client.get('/api/templates')
            templates = response.get_json()['templates']
            assert any(t['id'] == template_id for t in templates)
    
    def test_checkpoint_config_persist_across_requests(self, client, app):
        """测试检查点配置跨请求持久化"""
        # 保存配置
        client.post(
            '/api/checkpoint-config',
            json={'checkpoints': [{'id': 'persist-test', 'question': '持久化问题', 'enabled': True}]},
            content_type='application/json'
        )
        
        # 多次获取验证
        for _ in range(3):
            response = client.get('/api/checkpoint-config')
            checkpoints = response.get_json()['checkpoints']
            assert any(cp['id'] == 'persist-test' for cp in checkpoints)


class TestConcurrentAccess:
    """并发访问测试"""
    
    def test_concurrent_corrections_same_job(self, client, app):
        """测试同一任务的并发修正"""
        job_id = f'concurrent-{int(time.time())}'
        
        # 模拟并发保存不同 block 的修正
        for i in range(5):
            response = client.post(
                f'/api/corrections/{job_id}',
                json={'blockIndex': i, 'correctedText': f'并发修正 {i}'},
                content_type='application/json'
            )
            assert response.status_code == 200
        
        # 验证所有修正都已保存
        response = client.get(f'/api/corrections/{job_id}')
        assert response.get_json()['count'] == 5
    
    def test_concurrent_corrections_different_jobs(self, client, app):
        """测试不同任务的并发修正"""
        base_time = int(time.time())
        
        # 为多个任务保存修正
        for i in range(3):
            job_id = f'concurrent-job-{base_time}-{i}'
            client.post(
                f'/api/corrections/{job_id}',
                json={'blockIndex': 0, 'correctedText': f'任务 {i} 修正'},
                content_type='application/json'
            )
        
        # 验证每个任务的修正独立
        for i in range(3):
            job_id = f'concurrent-job-{base_time}-{i}'
            response = client.get(f'/api/corrections/{job_id}')
            corrections = response.get_json()['corrections']
            
            assert len(corrections) == 1
            assert corrections[0]['correctedText'] == f'任务 {i} 修正'
