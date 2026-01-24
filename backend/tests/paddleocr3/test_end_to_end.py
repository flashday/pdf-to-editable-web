#!/usr/bin/env python
"""
端到端测试脚本
测试完整的工作流：文件上传 -> OCR 处理 -> Editor.js 数据生成
"""
import sys
import os
import time
import requests
from pathlib import Path
from io import BytesIO
from PyPDF2 import PdfWriter

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

def create_test_pdf():
    """创建测试 PDF 文件"""
    output = PdfWriter()
    output.add_blank_page(width=612, height=792)
    
    pdf_bytes = BytesIO()
    output.write(pdf_bytes)
    pdf_bytes.seek(0)
    
    return pdf_bytes

def test_health_check(base_url):
    """测试健康检查端点"""
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("   ✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}")
        return False

def test_file_upload(base_url, pdf_file):
    """测试文件上传"""
    print("\n2. 测试文件上传...")
    try:
        files = {'file': ('test.pdf', pdf_file, 'application/pdf')}
        response = requests.post(f"{base_url}/api/convert", files=files)
        
        assert response.status_code == 202
        data = response.json()
        assert 'job_id' in data
        assert data['status'] == 'pending'
        
        job_id = data['job_id']
        print(f"   ✅ 文件上传成功，Job ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"   ❌ 文件上传失败: {e}")
        return None

def test_status_polling(base_url, job_id, max_attempts=30):
    """测试状态轮询"""
    print("\n3. 测试状态轮询...")
    try:
        for attempt in range(max_attempts):
            response = requests.get(f"{base_url}/api/convert/{job_id}/status")
            assert response.status_code == 200
            
            data = response.json()
            status = data.get('status')
            progress = data.get('progress', 0)
            message = data.get('message', '')
            
            print(f"   状态: {status}, 进度: {progress:.1f}%, 消息: {message}")
            
            if data.get('completed'):
                print("   ✅ 处理完成")
                return True
            
            if data.get('failed'):
                error = data.get('error', 'Unknown error')
                print(f"   ❌ 处理失败: {error}")
                return False
            
            time.sleep(2)
        
        print(f"   ⚠️ 超时：{max_attempts * 2} 秒后仍未完成")
        return False
    except Exception as e:
        print(f"   ❌ 状态轮询失败: {e}")
        return False

def test_get_result(base_url, job_id):
    """测试获取结果"""
    print("\n4. 测试获取结果...")
    try:
        response = requests.get(f"{base_url}/api/convert/{job_id}/result")
        
        # 可能返回 200（成功）、202（处理中）或 500（错误）
        if response.status_code == 202:
            print("   ⚠️ 处理仍在进行中")
            return None
        
        if response.status_code == 500:
            data = response.json()
            print(f"   ⚠️ 处理出错: {data.get('error', 'Unknown error')}")
            return None
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert 'result' in data
        assert 'blocks' in data['result']
        assert 'confidence_report' in data
        
        result = data['result']
        confidence = data['confidence_report']
        
        print(f"   ✅ 获取结果成功")
        print(f"   - 块数量: {len(result['blocks'])}")
        print(f"   - Editor.js 版本: {result.get('version', 'N/A')}")
        
        if confidence and 'confidence_breakdown' in confidence:
            overall = confidence['confidence_breakdown'].get('overall', {})
            score = overall.get('score', 0)
            level = overall.get('level', 'unknown')
            print(f"   - 置信度: {score:.2f} ({level})")
        
        return data
    except Exception as e:
        print(f"   ❌ 获取结果失败: {e}")
        return None

def test_invalid_file(base_url):
    """测试无效文件处理"""
    print("\n5. 测试无效文件处理...")
    try:
        # 测试无效文件类型
        files = {'file': ('test.txt', BytesIO(b'test content'), 'text/plain')}
        response = requests.post(f"{base_url}/api/convert", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        
        print(f"   ✅ 正确拒绝无效文件: {data['error']}")
        return True
    except Exception as e:
        print(f"   ❌ 无效文件处理测试失败: {e}")
        return False

def test_invalid_job_id(base_url):
    """测试无效 Job ID 处理"""
    print("\n6. 测试无效 Job ID 处理...")
    try:
        response = requests.get(f"{base_url}/api/convert/invalid-job-id/status")
        assert response.status_code == 404
        
        print("   ✅ 正确处理无效 Job ID")
        return True
    except Exception as e:
        print(f"   ❌ 无效 Job ID 处理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("PDF to Editable Web - 端到端测试")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # 检查服务器是否运行
    print("\n检查服务器状态...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ 服务器未运行或不健康")
            print("\n请先启动后端服务器：")
            print("  cd backend")
            print("  python app.py")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器")
        print("\n请先启动后端服务器：")
        print("  cd backend")
        print("  python app.py")
        return False
    
    print("✅ 服务器正在运行")
    
    # 运行测试
    results = []
    
    # 1. 健康检查
    results.append(("健康检查", test_health_check(base_url)))
    
    # 2. 文件上传
    pdf_file = create_test_pdf()
    job_id = test_file_upload(base_url, pdf_file)
    results.append(("文件上传", job_id is not None))
    
    if job_id:
        # 3. 状态轮询
        completed = test_status_polling(base_url, job_id)
        results.append(("状态轮询", completed))
        
        # 4. 获取结果
        if completed:
            result = test_get_result(base_url, job_id)
            results.append(("获取结果", result is not None))
    else:
        results.append(("状态轮询", False))
        results.append(("获取结果", False))
    
    # 5. 无效文件处理
    results.append(("无效文件处理", test_invalid_file(base_url)))
    
    # 6. 无效 Job ID 处理
    results.append(("无效 Job ID", test_invalid_job_id(base_url)))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:20s}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！端到端工作流正常运行。")
        return True
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
