"""
精准作业台 API 测试
测试布局数据、Markdown 锚点注入和内容保存 API
"""
import pytest
import json
import tempfile
from pathlib import Path


class TestLayoutWithAnchorsAPI:
    """布局数据 API 测试"""
    
    def test_get_layout_empty(self, client, app):
        """测试获取不存在的布局数据"""
        response = client.get('/api/convert/nonexistent-job/layout-with-anchors')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['blocks'] == []
        assert data['data']['imageWidth'] > 0
        assert data['data']['imageHeight'] > 0
    
    def test_get_layout_with_ppstructure(self, client, app):
        """测试从 ppstructure.json 获取布局数据"""
        job_id = 'test-layout-001'
        
        # 创建测试 ppstructure.json
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {
                'type': 'title',
                'bbox': [100, 50, 500, 80],
                'score': 0.95,
                'res': [{'text': '文档标题'}]
            },
            {
                'type': 'text',
                'bbox': [100, 100, 500, 300],
                'score': 0.87,
                'res': [{'text': '这是正文内容'}]
            },
            {
                'type': 'table',
                'bbox': [100, 320, 500, 500],
                'score': 0.92,
                'res': {'html': '<table><tr><td>A</td><td>B</td></tr></table>'}
            }
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/layout-with-anchors')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']['blocks']) == 3
        
        # 验证第一个 block
        block1 = data['data']['blocks'][0]
        assert block1['id'] == 'block_001'
        assert block1['type'] == 'title'
        assert block1['bbox']['x'] == 100
        assert block1['bbox']['y'] == 50
        assert block1['confidence'] == 0.95
        assert block1['text'] == '文档标题'
        
        # 验证第二个 block
        block2 = data['data']['blocks'][1]
        assert block2['id'] == 'block_002'
        assert block2['type'] == 'text'
        
        # 验证第三个 block（表格）
        block3 = data['data']['blocks'][2]
        assert block3['id'] == 'block_003'
        assert block3['type'] == 'table'
    
    def test_get_layout_block_id_format(self, client, app):
        """测试 Block ID 格式正确性"""
        job_id = 'test-layout-002'
        
        # 创建包含多个 block 的测试数据
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {'type': 'text', 'bbox': [0, i * 100, 100, (i + 1) * 100], 'score': 0.9}
            for i in range(15)
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/layout-with-anchors')
        data = response.get_json()
        
        # 验证 Block ID 格式（三位数字，前导零）
        assert data['data']['blocks'][0]['id'] == 'block_001'
        assert data['data']['blocks'][9]['id'] == 'block_010'
        assert data['data']['blocks'][14]['id'] == 'block_015'
    
    def test_get_layout_type_mapping(self, client, app):
        """测试类型映射正确性"""
        job_id = 'test-layout-003'
        
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {'type': 'title', 'bbox': [0, 0, 100, 50], 'score': 0.9},
            {'type': 'doc_title', 'bbox': [0, 50, 100, 100], 'score': 0.9},
            {'type': 'header', 'bbox': [0, 100, 100, 150], 'score': 0.9},
            {'type': 'footer', 'bbox': [0, 150, 100, 200], 'score': 0.9},
            {'type': 'figure', 'bbox': [0, 200, 100, 250], 'score': 0.9},
            {'type': 'equation', 'bbox': [0, 250, 100, 300], 'score': 0.9},
            {'type': 'unknown_type', 'bbox': [0, 300, 100, 350], 'score': 0.9},
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/layout-with-anchors')
        data = response.get_json()
        blocks = data['data']['blocks']
        
        assert blocks[0]['type'] == 'title'
        assert blocks[1]['type'] == 'title'  # doc_title -> title
        assert blocks[2]['type'] == 'header'
        assert blocks[3]['type'] == 'footer'
        assert blocks[4]['type'] == 'figure'
        assert blocks[5]['type'] == 'equation'
        assert blocks[6]['type'] == 'text'  # unknown -> text


class TestMarkdownWithAnchorsAPI:
    """Markdown 锚点注入 API 测试"""
    
    def test_get_markdown_empty(self, client, app):
        """测试获取不存在的 Markdown"""
        response = client.get('/api/convert/nonexistent-job/markdown-with-anchors')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert '无内容' in data['data']['markdown'] or '无 OCR' in data['data']['markdown']
    
    def test_get_markdown_with_anchors(self, client, app):
        """测试生成带锚点的 Markdown"""
        job_id = 'test-md-001'
        
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {
                'type': 'title',
                'bbox': [100, 50, 500, 80],
                'score': 0.95,
                'res': [{'text': '文档标题'}]
            },
            {
                'type': 'text',
                'bbox': [100, 100, 500, 300],
                'score': 0.87,
                'res': [{'text': '这是正文内容'}]
            }
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/markdown-with-anchors')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        markdown = data['data']['markdown']
        anchors = data['data']['anchors']
        
        # 验证锚点存在（使用新的统一格式：<!-- @block:block_xxx x,y,width,height -->）
        assert '<!-- @block:block_001 ' in markdown
        assert '<!-- @block:block_002 ' in markdown
        
        # 验证内容
        assert '# 文档标题' in markdown
        assert '这是正文内容' in markdown
        
        # 验证锚点索引
        assert len(anchors) == 2
        assert anchors[0]['blockId'] == 'block_001'
        assert anchors[1]['blockId'] == 'block_002'
    
    def test_get_markdown_anchor_format(self, client, app):
        """测试锚点格式正确性"""
        job_id = 'test-md-002'
        
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {
                'type': 'text',
                'bbox': [50, 100, 450, 200],
                'score': 0.9,
                'res': 'Test content'
            }
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/markdown-with-anchors')
        data = response.get_json()
        
        markdown = data['data']['markdown']
        
        # 验证锚点格式：<!-- @block:block_xxx x,y,width,height -->
        import re
        anchor_pattern = r'<!-- @block:block_\d{3} \d+,\d+,\d+,\d+ -->'
        matches = re.findall(anchor_pattern, markdown)
        assert len(matches) == 1
    
    def test_get_markdown_table_conversion(self, client, app):
        """测试表格转换为 Markdown"""
        job_id = 'test-md-003'
        
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {
                'type': 'table',
                'bbox': [100, 100, 500, 300],
                'score': 0.92,
                'res': {
                    'html': '<table><tr><th>列1</th><th>列2</th></tr><tr><td>A</td><td>B</td></tr></table>'
                }
            }
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        response = client.get(f'/api/convert/{job_id}/markdown-with-anchors')
        data = response.get_json()
        
        markdown = data['data']['markdown']
        
        # 验证表格转换为 Markdown 格式
        assert '|' in markdown
        assert '---' in markdown
        assert '列1' in markdown
        assert '列2' in markdown


class TestSaveMarkdownAPI:
    """内容保存 API 测试"""
    
    def test_save_markdown_success(self, client, app):
        """测试保存 Markdown 成功"""
        job_id = 'test-save-001'
        markdown_content = '# 测试标题\n\n这是测试内容。'
        
        response = client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={'markdown': markdown_content},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'savedAt' in data['data']
        assert 'filePath' in data['data']
        
        # 验证文件已保存
        temp_folder = app.config['TEMP_FOLDER']
        saved_path = temp_folder / f"{job_id}_corrected.md"
        assert saved_path.exists()
        
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        assert saved_content == markdown_content
    
    def test_save_markdown_empty_content(self, client):
        """测试保存空内容"""
        response = client.post(
            '/api/convert/test-job/save-markdown',
            json={'markdown': ''},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_save_markdown_no_data(self, client):
        """测试无数据请求"""
        response = client.post(
            '/api/convert/test-job/save-markdown',
            data='invalid',
            content_type='application/json'
        )
        
        assert response.status_code in [400, 500]
    
    def test_save_markdown_with_vector_update(self, client, app):
        """测试保存并更新向量库"""
        job_id = 'test-save-002'
        
        response = client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={
                'markdown': '# 测试\n\n内容',
                'updateVector': True
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # vectorUpdated 可能为 True 或 False，取决于向量库是否可用
        assert 'vectorUpdated' in data['data']
    
    def test_save_markdown_overwrite(self, client, app):
        """测试覆盖保存"""
        job_id = 'test-save-003'
        
        # 第一次保存
        client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={'markdown': '第一次内容'},
            content_type='application/json'
        )
        
        # 第二次保存（覆盖）
        response = client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={'markdown': '第二次内容'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # 验证内容已被覆盖
        temp_folder = app.config['TEMP_FOLDER']
        saved_path = temp_folder / f"{job_id}_corrected.md"
        
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        assert saved_content == '第二次内容'
    
    def test_save_markdown_timestamp_format(self, client, app):
        """测试保存时间戳格式"""
        job_id = 'test-save-004'
        
        response = client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={'markdown': '测试内容'},
            content_type='application/json'
        )
        
        data = response.get_json()
        saved_at = data['data']['savedAt']
        
        # 验证 ISO 8601 格式
        import re
        iso_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
        assert re.match(iso_pattern, saved_at)


class TestWorkbenchAPIIntegration:
    """精准作业台 API 集成测试"""
    
    def test_full_workflow(self, client, app):
        """测试完整工作流：获取布局 -> 获取 Markdown -> 编辑 -> 保存"""
        job_id = 'test-workflow-001'
        
        # 准备测试数据
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {
                'type': 'title',
                'bbox': [100, 50, 500, 80],
                'score': 0.95,
                'res': [{'text': '原始标题'}]
            },
            {
                'type': 'text',
                'bbox': [100, 100, 500, 300],
                'score': 0.87,
                'res': [{'text': '原始内容'}]
            }
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        # 1. 获取布局数据
        layout_response = client.get(f'/api/convert/{job_id}/layout-with-anchors')
        assert layout_response.status_code == 200
        layout_data = layout_response.get_json()
        assert len(layout_data['data']['blocks']) == 2
        
        # 2. 获取带锚点的 Markdown
        md_response = client.get(f'/api/convert/{job_id}/markdown-with-anchors')
        assert md_response.status_code == 200
        md_data = md_response.get_json()
        original_markdown = md_data['data']['markdown']
        assert '原始标题' in original_markdown
        
        # 3. 模拟编辑：修改内容
        edited_markdown = original_markdown.replace('原始标题', '修正后的标题')
        edited_markdown = edited_markdown.replace('原始内容', '修正后的内容')
        
        # 4. 保存修正后的内容
        save_response = client.post(
            f'/api/convert/{job_id}/save-markdown',
            json={'markdown': edited_markdown},
            content_type='application/json'
        )
        assert save_response.status_code == 200
        
        # 5. 验证保存的内容
        saved_path = temp_folder / f"{job_id}_corrected.md"
        with open(saved_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert '修正后的标题' in saved_content
        assert '修正后的内容' in saved_content
    
    def test_block_id_consistency(self, client, app):
        """测试 Block ID 在布局和 Markdown 中的一致性"""
        job_id = 'test-consistency-001'
        
        temp_folder = app.config['TEMP_FOLDER']
        ppstructure_data = [
            {'type': 'title', 'bbox': [0, 0, 100, 50], 'score': 0.9, 'res': 'Title'},
            {'type': 'text', 'bbox': [0, 60, 100, 150], 'score': 0.85, 'res': 'Text'},
        ]
        
        ppstructure_path = temp_folder / f"{job_id}_ppstructure.json"
        with open(ppstructure_path, 'w', encoding='utf-8') as f:
            json.dump(ppstructure_data, f)
        
        # 获取布局数据
        layout_response = client.get(f'/api/convert/{job_id}/layout-with-anchors')
        layout_blocks = layout_response.get_json()['data']['blocks']
        
        # 获取 Markdown 锚点
        md_response = client.get(f'/api/convert/{job_id}/markdown-with-anchors')
        md_anchors = md_response.get_json()['data']['anchors']
        
        # 验证 Block ID 一致
        layout_ids = [b['id'] for b in layout_blocks]
        anchor_ids = [a['blockId'] for a in md_anchors]
        
        assert layout_ids == anchor_ids
