# PDF to Editable Web - 完整安装指南

## 📋 系统要求

### 必需环境
- **操作系统**: Windows 11 或 macOS 13+
- **Python 版本**: **3.10.11** (强烈推荐) 或 3.9.13
- **Node.js**: 14.x 或更高版本
- **内存**: 至少 4GB RAM
- **磁盘空间**: 至少 2GB 可用空间

### ⚠️ 重要提示
- **不要使用 Python 3.12+** - PaddleOCR 不兼容
- **不要使用 Python 3.14** - 多个依赖不兼容
- **推荐使用 Python 3.10.11** - 最佳兼容性和稳定性

## 🔧 安装步骤

### 第一步：安装 Python 3.10.11

#### Windows 安装
1. 下载 Python 3.10.11:
   - 访问: https://www.python.org/downloads/release/python-31011/
   - 下载: `python-3.10.11-amd64.exe`

2. 安装配置:
   ```
   ✅ Add Python 3.10 to PATH
   ✅ Install for all users (可选)
   选择 "Customize installation"
   ✅ pip
   ✅ py launcher
   安装位置: C:\Python310 (推荐)
   ```

3. 验证安装:
   ```powershell
   py -3.10 --version
   # 应显示: Python 3.10.11
   ```

#### macOS 安装
```bash
# 使用 Homebrew
brew install python@3.10

# 验证安装
python3.10 --version
```

### 第二步：克隆项目

```bash
git clone <your-repository-url>
cd pdf-to-editable-web
```

### 第三步：创建虚拟环境

#### Windows
```powershell
# 创建虚拟环境
py -3.10 -m venv venv310

# 激活虚拟环境
.\venv310\Scripts\Activate.ps1
# 或者在 CMD 中
.\venv310\Scripts\activate.bat
```

#### macOS/Linux
```bash
# 创建虚拟环境
python3.10 -m venv venv310

# 激活虚拟环境
source venv310/bin/activate
```

### 第四步：升级 pip

```bash
python -m pip install --upgrade pip
```

### 第五步：安装后端依赖

#### 方法 1: 使用国内镜像（推荐，速度快）

```bash
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 方法 2: 使用官方源

```bash
cd backend
pip install -r requirements.txt
```

#### 预期安装时间
- 使用国内镜像: 约 3-5 分钟
- 使用官方源: 约 10-15 分钟

### 第六步：验证核心组件

```bash
# 验证 PaddleOCR
python -c "import paddleocr; print('PaddleOCR OK')"

# 验证 PaddlePaddle
python -c "import paddle; print('PaddlePaddle OK')"

# 验证其他核心组件
python -c "import flask; import pydantic; print('All core components OK')"
```

如果所有命令都输出 "OK"，说明后端依赖安装成功！

### 第七步：安装前端依赖

```bash
cd ../frontend
npm install
```

预期安装时间: 约 2-3 分钟

### 第八步：运行测试验证

#### 后端测试
```bash
cd ../backend
python -m pytest tests/test_models.py -v
```

预期结果: 6/6 测试通过

#### 前端测试
```bash
cd ../frontend
npm test
```

预期结果: 83/83 测试通过

## 📦 依赖版本清单

### 后端核心依赖（已验证）

```txt
# Python 版本
Python==3.10.11

# Web 框架
Flask==3.0.0
Flask-CORS==4.0.0

# OCR 引擎（关键）
paddlepaddle==2.6.2
paddleocr==2.7.0.3
opencv-python==4.6.0.66
numpy>=1.24.3,<2.0

# 文件处理
PyPDF2==3.0.1
Pillow==10.1.0
PyMuPDF==1.20.2

# 数据处理
pydantic==2.5.0
jsonschema==4.20.0
beautifulsoup4==4.12.2
chardet==5.2.0

# 测试框架
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
hypothesis==6.92.1

# 其他
requests==2.31.0
psutil==5.9.6
python-dotenv==1.0.0
```

### 前端核心依赖

```json
{
  "@editorjs/editorjs": "^2.28.2",
  "@editorjs/header": "^2.7.0",
  "@editorjs/paragraph": "^2.10.0",
  "@editorjs/table": "^2.2.2",
  "axios": "^1.6.2"
}
```

## 🔍 常见问题排查

### 问题 1: PaddleOCR 安装失败

**症状**: 
```
ERROR: Could not find a version that satisfies the requirement paddlepaddle
```

**解决方案**:
1. 确认 Python 版本是 3.10.x
2. 使用国内镜像源:
   ```bash
   pip install paddlepaddle==2.6.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install paddleocr==2.7.0.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### 问题 2: NumPy 版本冲突

**症状**:
```
RuntimeError: module compiled against ABI version 0x1000009 but this version of numpy is 0x2000000
```

**解决方案**:
```bash
pip install "numpy>=1.24.3,<2.0" --force-reinstall
```

### 问题 3: OpenCV 导入错误

**症状**:
```
ImportError: numpy.core.multiarray failed to import
```

**解决方案**:
1. 确保 numpy < 2.0
2. 重新安装 opencv-python:
   ```bash
   pip uninstall opencv-python opencv-python-headless
   pip install opencv-python==4.6.0.66
   ```

### 问题 4: Pillow 版本不兼容

**症状**:
```
ImportError: cannot import name 'PILLOW_VERSION' from 'PIL'
```

**解决方案**:
```bash
pip install Pillow==10.1.0 --force-reinstall
```

### 问题 5: Windows 测试文件权限错误

**症状**:
```
PermissionError: [WinError 32] 另一个程序正在使用此文件
```

**解决方案**:
这是 Windows 的已知问题，不影响功能。可以忽略这些错误。

## 🚀 启动项目

### 启动后端服务

```bash
# 激活虚拟环境
.\venv310\Scripts\Activate.ps1  # Windows
# 或
source venv310/bin/activate      # macOS/Linux

# 启动后端
cd backend
python app.py
```

后端服务将在 http://localhost:5000 启动

### 启动前端服务

```bash
# 在另一个终端
cd frontend
npm run dev
```

前端服务将在 http://localhost:3000 启动

## 📝 版本兼容性矩阵

| 组件 | Python 3.9 | Python 3.10 | Python 3.11 | Python 3.12+ |
|------|-----------|------------|------------|-------------|
| PaddlePaddle 2.6.2 | ✅ | ✅ | ✅ | ❌ |
| PaddleOCR 2.7.0.3 | ✅ | ✅ | ✅ | ❌ |
| NumPy 1.26.4 | ✅ | ✅ | ✅ | ❌ |
| Pillow 10.1.0 | ✅ | ✅ | ✅ | ⚠️ |
| Flask 3.0.0 | ✅ | ✅ | ✅ | ✅ |
| Pydantic 2.5.0 | ✅ | ✅ | ✅ | ✅ |
| **推荐度** | 🥈 | 🏆 | ⚠️ | ❌ |

**图例**:
- ✅ 完全支持
- ⚠️ 部分支持或需要特殊配置
- ❌ 不支持
- 🏆 最佳选择
- 🥈 次优选择

## 🔄 换电脑安装清单

### 准备工作
- [ ] 确认新电脑操作系统版本
- [ ] 下载 Python 3.10.11 安装包
- [ ] 安装 Git
- [ ] 安装 Node.js (14.x+)

### 安装步骤
- [ ] 安装 Python 3.10.11
- [ ] 验证 Python 版本: `py -3.10 --version`
- [ ] 克隆项目仓库
- [ ] 创建虚拟环境: `py -3.10 -m venv venv310`
- [ ] 激活虚拟环境
- [ ] 升级 pip: `python -m pip install --upgrade pip`
- [ ] 安装后端依赖: `pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- [ ] 验证 PaddleOCR: `python -c "import paddleocr; print('OK')"`
- [ ] 安装前端依赖: `cd frontend && npm install`
- [ ] 运行后端测试: `python -m pytest backend/tests/test_models.py -v`
- [ ] 运行前端测试: `cd frontend && npm test`

### 验证清单
- [ ] 后端测试通过 (至少 6/6 基础测试)
- [ ] 前端测试通过 (83/83)
- [ ] PaddleOCR 可以导入
- [ ] 后端服务可以启动
- [ ] 前端服务可以启动

## 📚 相关文档

- `DEPENDENCY_INSTALLATION_COMPLETE.md` - 详细的安装完成报告
- `PYTHON_VERSION_COMPATIBILITY_ANALYSIS.md` - Python 版本兼容性分析
- `backend/requirements.txt` - 后端依赖清单
- `frontend/package.json` - 前端依赖清单

## 💡 最佳实践

### 1. 使用虚拟环境
始终在虚拟环境中工作，避免污染系统 Python 环境。

### 2. 固定版本号
requirements.txt 中已固定所有版本号，确保环境一致性。

### 3. 使用国内镜像
在中国大陆使用清华镜像源可以显著提升安装速度。

### 4. 定期更新依赖
定期检查依赖更新，但要在测试环境中验证后再更新生产环境。

### 5. 备份虚拟环境配置
可以使用以下命令导出完整的依赖列表：
```bash
pip freeze > requirements-freeze.txt
```

## 🆘 获取帮助

如果遇到安装问题：

1. 检查 Python 版本是否为 3.10.11
2. 查看本文档的"常见问题排查"部分
3. 查看 `DEPENDENCY_INSTALLATION_COMPLETE.md` 中的详细安装日志
4. 确保使用了国内镜像源（如果在中国大陆）

## 📅 更新日志

### 2026-01-18
- ✅ 初始版本
- ✅ 验证 Python 3.10.11 兼容性
- ✅ 确认所有依赖版本
- ✅ 完成完整安装测试

---

**文档版本**: 1.0
**最后更新**: 2026-01-18
**维护者**: Kiro AI Assistant
