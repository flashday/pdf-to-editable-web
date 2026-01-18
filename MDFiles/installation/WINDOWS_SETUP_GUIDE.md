# Windows 11 安装和运行指南

本指南专门针对 Windows 11 专业版用户。

## 📋 前置要求

### 1. 安装 Python 3.8+

**下载地址**: https://www.python.org/downloads/

**安装步骤**:
1. 下载 Python 3.8 或更高版本
2. 运行安装程序
3. ⚠️ **重要**: 勾选 "Add Python to PATH"
4. 点击 "Install Now"

**验证安装**:
```cmd
python --version
```
应该显示类似 `Python 3.11.x`

### 2. 安装 Node.js 16+

**下载地址**: https://nodejs.org/

**安装步骤**:
1. 下载 LTS 版本（推荐）
2. 运行安装程序
3. 使用默认设置安装

**验证安装**:
```cmd
node --version
npm --version
```

### 3. 安装 Git（可选，用于克隆仓库）

**下载地址**: https://git-scm.com/download/win

## 📥 下载项目

### 方法 1: 使用 Git（推荐）

打开 PowerShell 或 CMD：

```cmd
git clone https://github.com/flashday/pdf-to-editable-web.git
cd pdf-to-editable-web
```

### 方法 2: 下载 ZIP

1. 访问 https://github.com/flashday/pdf-to-editable-web
2. 点击绿色的 "Code" 按钮
3. 选择 "Download ZIP"
4. 解压到你想要的目录
5. 在该目录打开 PowerShell 或 CMD

## 🚀 快速启动

### 方法 1: 使用 Python 脚本（推荐，跨平台）

```cmd
python run_dev.py
```

这个脚本会自动：
- 创建虚拟环境
- 安装所有依赖
- 启动后端和前端服务器

### 方法 2: 使用批处理脚本

```cmd
run_dev.bat
```

### 方法 3: 手动启动（如果自动脚本失败）

#### 步骤 1: 创建虚拟环境

```cmd
python -m venv venv
```

#### 步骤 2: 激活虚拟环境

```cmd
venv\Scripts\activate
```

你应该看到命令提示符前面出现 `(venv)`

#### 步骤 3: 安装 Python 依赖

```cmd
pip install -r backend\requirements.txt
```

#### 步骤 4: 安装 PaddleOCR（必需）

```cmd
pip install paddleocr paddlepaddle
```

⚠️ **注意**: 这一步会下载约 200-300MB，需要 10-20 分钟

#### 步骤 5: 启动后端（新开一个终端窗口）

```cmd
python start_backend.py
```

后端将在 http://localhost:5000 运行

#### 步骤 6: 安装前端依赖（新开另一个终端窗口）

```cmd
cd frontend
npm install
```

#### 步骤 7: 启动前端

```cmd
npm run dev
```

前端将在 http://localhost:3000 或 http://127.0.0.1:3000 运行

## 🌐 访问应用

打开浏览器访问：
- **推荐**: http://127.0.0.1:3000
- 或: http://localhost:3000

## ⚠️ Windows 特定问题和解决方案

### 问题 1: "python" 命令未找到

**解决方案**:
1. 确保安装 Python 时勾选了 "Add Python to PATH"
2. 或者使用 `py` 命令代替 `python`：
   ```cmd
   py run_dev.py
   ```

### 问题 2: 虚拟环境激活失败

**错误信息**: "无法加载文件，因为在此系统上禁止运行脚本"

**解决方案**:
以管理员身份运行 PowerShell，执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

然后重新激活虚拟环境：
```cmd
venv\Scripts\activate
```

### 问题 3: 端口被占用

**错误信息**: "Address already in use" 或 "端口已被占用"

**解决方案**:

查找占用端口的进程：
```cmd
netstat -ano | findstr :5000
netstat -ano | findstr :3000
```

终止进程（替换 PID 为实际的进程 ID）：
```cmd
taskkill /PID <PID> /F
```

### 问题 4: 防火墙阻止

**解决方案**:
1. Windows 可能会弹出防火墙警告
2. 点击 "允许访问"
3. 确保允许 Python 和 Node.js 通过防火墙

### 问题 5: 中文文件名乱码

**解决方案**:
Windows 默认应该支持 UTF-8，但如果遇到问题：

1. 在 PowerShell 中设置编码：
   ```powershell
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

2. 或在 CMD 中：
   ```cmd
   chcp 65001
   ```

### 问题 6: PaddleOCR 安装失败

**解决方案**:

如果遇到编译错误，尝试安装预编译版本：
```cmd
pip install paddleocr paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
```

或使用国内镜像：
```cmd
pip install paddleocr paddlepaddle -i https://mirrors.aliyun.com/pypi/simple/
```

## 📝 运行测试

### 后端测试

```cmd
cd backend
pytest -v
```

### 前端测试

```cmd
cd frontend
npm test
```

## 🛑 停止服务器

### 如果使用 run_dev.py 或 run_dev.bat

按 `Ctrl+C` 停止所有服务器

### 如果手动启动

在每个终端窗口按 `Ctrl+C`

## 📂 目录结构

```
pdf-to-editable-web/
├── backend/              # Python 后端
│   ├── api/             # API 路由
│   ├── services/        # 业务逻辑
│   ├── tests/           # 后端测试
│   └── requirements.txt # Python 依赖
├── frontend/            # JavaScript 前端
│   ├── src/            # 源代码
│   └── package.json    # Node.js 依赖
├── uploads/            # 上传文件目录（自动创建）
├── temp/               # 临时文件目录（自动创建）
├── logs/               # 日志目录（自动创建）
├── run_dev.py          # 跨平台启动脚本（推荐）
├── run_dev.bat         # Windows 批处理脚本
├── run_dev.sh          # macOS/Linux 脚本
└── start_backend.py    # 后端启动脚本
```

## 🔧 开发工具推荐

### IDE/编辑器
- **VS Code** (推荐): https://code.visualstudio.com/
- **PyCharm**: https://www.jetbrains.com/pycharm/

### VS Code 扩展推荐
- Python
- Pylance
- ESLint
- Prettier

## 📞 需要帮助？

如果遇到问题：

1. 查看 `TROUBLESHOOTING.md` 文件
2. 检查 `logs/error.log` 日志文件
3. 在 GitHub 上提交 Issue: https://github.com/flashday/pdf-to-editable-web/issues

## ✅ 验证安装

运行以下命令验证所有组件：

```cmd
python --version
node --version
npm --version
pip list | findstr flask
pip list | findstr paddleocr
```

全部成功后，你就可以开始使用系统了！🎉
