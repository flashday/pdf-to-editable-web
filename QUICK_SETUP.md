# 快速安装参考卡

## 🎯 一键复制命令

### Windows 完整安装流程

```powershell
# 1. 验证 Python 版本（必须是 3.10.x）
py -3.10 --version

# 2. 创建虚拟环境
py -3.10 -m venv venv310

# 3. 激活虚拟环境
.\venv310\Scripts\Activate.ps1

# 4. 升级 pip
python -m pip install --upgrade pip

# 5. 安装后端依赖（使用国内镜像）
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 6. 验证安装
python -c "import paddleocr; print('PaddleOCR OK')"

# 7. 安装前端依赖
cd ..\frontend
npm install

# 8. 运行测试
cd ..\backend
python -m pytest tests\test_models.py -v
```

### macOS/Linux 完整安装流程

```bash
# 1. 验证 Python 版本
python3.10 --version

# 2. 创建虚拟环境
python3.10 -m venv venv310

# 3. 激活虚拟环境
source venv310/bin/activate

# 4. 升级 pip
python -m pip install --upgrade pip

# 5. 安装后端依赖
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 6. 验证安装
python -c "import paddleocr; print('PaddleOCR OK')"

# 7. 安装前端依赖
cd ../frontend
npm install

# 8. 运行测试
cd ../backend
python -m pytest tests/test_models.py -v
```

## 📋 关键版本信息

```
Python: 3.10.11 (必需)
PaddlePaddle: 2.6.2
PaddleOCR: 2.7.0.3
NumPy: 1.26.4 (必须 < 2.0)
OpenCV: 4.6.0.66
Pillow: 10.1.0
PyMuPDF: 1.20.2
Flask: 3.0.0
```

## 🚀 启动命令

### 启动后端
```bash
# Windows
.\venv310\Scripts\Activate.ps1
cd backend
python app.py

# macOS/Linux
source venv310/bin/activate
cd backend
python app.py
```

### 启动前端
```bash
cd frontend
npm run dev
```

## ⚠️ 常见错误快速修复

### NumPy 版本冲突
```bash
pip install "numpy>=1.24.3,<2.0" --force-reinstall
```

### PaddleOCR 导入失败
```bash
pip install paddlepaddle==2.6.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install paddleocr==2.7.0.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Pillow 版本问题
```bash
pip install Pillow==10.1.0 --force-reinstall
```

## ✅ 验证清单

- [ ] Python 版本 = 3.10.11
- [ ] 虚拟环境已创建
- [ ] 后端依赖已安装
- [ ] PaddleOCR 可导入
- [ ] 前端依赖已安装
- [ ] 基础测试通过

## 📞 下载链接

- Python 3.10.11: https://www.python.org/downloads/release/python-31011/
- Node.js: https://nodejs.org/

---
**提示**: 详细说明请查看 `INSTALLATION_GUIDE.md`
