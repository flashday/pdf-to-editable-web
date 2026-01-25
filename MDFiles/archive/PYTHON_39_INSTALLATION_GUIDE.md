# Python 3.9 安装和配置指南

## 当前状态
- 系统当前 Python 版本: 3.14.0
- 需要安装: Python 3.9.x
- 原因: PaddleOCR 不支持 Python 3.14

## 安装步骤

### 方法 1: 使用官方安装包（推荐）

1. **下载 Python 3.9**
   - 访问: https://www.python.org/downloads/release/python-3913/
   - 下载: Windows installer (64-bit)
   - 文件名: python-3.9.13-amd64.exe

2. **安装 Python 3.9**
   ```
   - 运行下载的安装程序
   - ✅ 勾选 "Add Python 3.9 to PATH"
   - ✅ 勾选 "Install for all users" (可选)
   - 选择 "Customize installation"
   - ✅ 确保勾选 "pip"
   - ✅ 确保勾选 "py launcher"
   - 安装位置建议: C:\Python39
   - 点击 "Install"
   ```

3. **验证安装**
   ```powershell
   # 打开新的 PowerShell 窗口
   py -3.9 --version
   # 应该显示: Python 3.9.13
   ```

### 方法 2: 使用 Chocolatey

如果您已安装 Chocolatey 包管理器：

```powershell
# 以管理员身份运行 PowerShell
choco install python39 -y

# 验证安装
py -3.9 --version
```

### 方法 3: 使用 Microsoft Store

1. 打开 Microsoft Store
2. 搜索 "Python 3.9"
3. 点击安装
4. 等待安装完成

## 安装后配置

### 1. 创建 Python 3.9 虚拟环境

```powershell
# 进入项目目录
cd D:\PrivatePrj\pdf-to-editable-web

# 创建虚拟环境
py -3.9 -m venv venv39

# 激活虚拟环境
.\venv39\Scripts\activate

# 验证 Python 版本
python --version
# 应该显示: Python 3.9.x
```

### 2. 升级 pip

```powershell
python -m pip install --upgrade pip
```

### 3. 安装项目依赖

```powershell
# 确保在虚拟环境中
cd backend

# 安装所有依赖
pip install -r requirements.txt
```

### 4. 验证 PaddleOCR 安装

```powershell
# 测试 PaddleOCR 导入
python -c "import paddleocr; print('PaddleOCR installed successfully')"
```

## 更新 requirements.txt

由于 Python 3.9 的兼容性，可能需要调整某些包的版本：

```txt
# Core dependencies
Flask==3.0.0
Flask-CORS==4.0.0

# Network and HTTP
requests==2.31.0

# System monitoring
psutil==5.9.6

# File processing
PyPDF2==3.0.1
Pillow==10.1.0  # Python 3.9 兼容版本
PyMuPDF==1.23.8

# OCR dependencies
paddlepaddle==2.5.2
paddleocr==2.7.0.3
opencv-python==4.8.1.78
numpy==1.24.3
beautifulsoup4==4.12.2

# Character encoding
chardet==5.2.0

# Data validation and serialization
pydantic==2.5.0
jsonschema==4.20.0

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
hypothesis==6.92.1

# Development
python-dotenv==1.0.0
```

## 快速安装脚本

创建一个批处理文件 `setup_python39.bat`:

```batch
@echo off
echo ========================================
echo Python 3.9 环境设置
echo ========================================

echo.
echo 步骤 1: 创建虚拟环境...
py -3.9 -m venv venv39

echo.
echo 步骤 2: 激活虚拟环境...
call venv39\Scripts\activate.bat

echo.
echo 步骤 3: 升级 pip...
python -m pip install --upgrade pip

echo.
echo 步骤 4: 安装后端依赖...
cd backend
pip install -r requirements.txt

echo.
echo 步骤 5: 验证安装...
python -c "import flask; print('Flask OK')"
python -c "import paddleocr; print('PaddleOCR OK')"
python -c "import numpy; print('NumPy OK')"

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用以下命令激活环境:
echo   venv39\Scripts\activate
echo.
pause
```

## 运行测试

安装完成后，运行测试验证：

```powershell
# 激活虚拟环境
.\venv39\Scripts\activate

# 运行后端测试
cd backend
python -m pytest tests/ -v

# 运行前端测试
cd ../frontend
npm test
```

## 常见问题

### 问题 1: PaddleOCR 安装失败

**解决方案:**
```powershell
# 先安装依赖
pip install numpy==1.24.3
pip install opencv-python==4.8.1.78

# 再安装 PaddlePaddle
pip install paddlepaddle==2.5.2 -i https://mirror.baidu.com/pypi/simple

# 最后安装 PaddleOCR
pip install paddleocr==2.7.0.3
```

### 问题 2: 虚拟环境激活失败

**解决方案:**
```powershell
# 允许执行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 重新激活
.\venv39\Scripts\activate
```

### 问题 3: pip 安装速度慢

**解决方案:**
```powershell
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 下一步

安装完成后，继续执行：

1. ✅ 运行完整的测试套件
2. ✅ 实现 23 个属性测试
3. ✅ 测试 OCR 功能
4. ✅ 执行端到端集成测试

---

**注意**: 安装 Python 3.9 后，请重新打开 PowerShell 窗口以确保环境变量生效。
