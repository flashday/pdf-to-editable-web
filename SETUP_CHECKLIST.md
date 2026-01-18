# 换电脑安装检查清单

## 📋 使用说明
在新电脑上安装项目时，按照此清单逐项检查，确保安装顺利。

---

## 第一阶段：准备工作

### 1.1 系统要求检查
- [ ] 操作系统: Windows 11 / macOS 13+ / Ubuntu 20.04+
- [ ] 内存: 至少 4GB RAM
- [ ] 磁盘空间: 至少 2GB 可用
- [ ] 网络连接: 正常

### 1.2 下载必需软件
- [ ] Python 3.10.11
  - Windows: https://www.python.org/downloads/release/python-31011/
  - 文件: `python-3.10.11-amd64.exe`
- [ ] Git (如果还没有)
- [ ] Node.js 14.x+ (如果还没有)

### 1.3 安装 Python 3.10.11
- [ ] 运行安装程序
- [ ] ✅ 勾选 "Add Python 3.10 to PATH"
- [ ] 选择 "Customize installation"
- [ ] ✅ 勾选 pip
- [ ] ✅ 勾选 py launcher
- [ ] 安装位置: C:\Python310 (Windows)

### 1.4 验证 Python 安装
```bash
py -3.10 --version
# 应显示: Python 3.10.11
```
- [ ] Python 版本正确

---

## 第二阶段：项目设置

### 2.1 获取项目代码
```bash
git clone <repository-url>
cd pdf-to-editable-web
```
- [ ] 项目已克隆
- [ ] 进入项目目录

### 2.2 创建虚拟环境
**Windows:**
```powershell
py -3.10 -m venv venv310
```

**macOS/Linux:**
```bash
python3.10 -m venv venv310
```
- [ ] 虚拟环境已创建
- [ ] venv310 文件夹存在

### 2.3 激活虚拟环境
**Windows PowerShell:**
```powershell
.\venv310\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.\venv310\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source venv310/bin/activate
```
- [ ] 虚拟环境已激活
- [ ] 命令提示符显示 (venv310)

### 2.4 升级 pip
```bash
python -m pip install --upgrade pip
```
- [ ] pip 已升级到最新版本

---

## 第三阶段：后端依赖安装

### 3.1 确认 requirements.txt 存在
```bash
ls backend/requirements.txt  # macOS/Linux
dir backend\requirements.txt  # Windows
```
- [ ] requirements.txt 文件存在

### 3.2 检查关键版本号
打开 `backend/requirements.txt`，确认以下版本：
- [ ] paddlepaddle==2.6.2
- [ ] paddleocr==2.7.0.3
- [ ] opencv-python==4.6.0.66
- [ ] numpy>=1.24.3,<2.0
- [ ] Pillow==10.1.0
- [ ] PyMuPDF==1.20.2

### 3.3 安装后端依赖

**方法 1: 使用国内镜像（推荐）**
```bash
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**方法 2: 使用官方源**
```bash
cd backend
pip install -r requirements.txt
```

- [ ] 依赖安装开始
- [ ] 等待 3-15 分钟（取决于网络）
- [ ] 安装完成，无错误

### 3.4 验证核心组件

**验证 PaddleOCR:**
```bash
python -c "import paddleocr; print('PaddleOCR OK')"
```
- [ ] 输出: PaddleOCR OK

**验证 PaddlePaddle:**
```bash
python -c "import paddle; print('PaddlePaddle OK')"
```
- [ ] 输出: PaddlePaddle OK

**验证 NumPy 版本:**
```bash
python -c "import numpy; print(f'NumPy {numpy.__version__}')"
```
- [ ] 输出: NumPy 1.26.x (必须 < 2.0)

**验证其他核心组件:**
```bash
python -c "import flask; import pydantic; print('All OK')"
```
- [ ] 输出: All OK

### 3.5 检查已安装的包
```bash
pip list | grep -E "paddle|opencv|numpy|Pillow|PyMuPDF"
```
- [ ] paddlepaddle 2.6.2
- [ ] paddleocr 2.7.0.3
- [ ] opencv-python 4.6.0.66
- [ ] numpy 1.26.x
- [ ] Pillow 10.1.0
- [ ] PyMuPDF 1.20.2

---

## 第四阶段：前端依赖安装

### 4.1 进入前端目录
```bash
cd ../frontend  # 如果在 backend 目录
# 或
cd frontend     # 如果在项目根目录
```
- [ ] 已进入 frontend 目录

### 4.2 安装前端依赖
```bash
npm install
```
- [ ] 依赖安装开始
- [ ] 等待 2-5 分钟
- [ ] 安装完成，无错误
- [ ] node_modules 文件夹已创建

### 4.3 检查关键包
```bash
npm list --depth=0 | grep -E "editorjs|axios"
```
- [ ] @editorjs/editorjs 存在
- [ ] axios 存在

---

## 第五阶段：测试验证

### 5.1 后端基础测试
```bash
cd ../backend  # 如果在 frontend 目录
python -m pytest tests/test_models.py -v
```
- [ ] 测试开始运行
- [ ] 6/6 测试通过
- [ ] 无错误

### 5.2 后端完整测试（可选）
```bash
python -m pytest tests/ -v --tb=short
```
- [ ] 至少 150+ 测试通过
- [ ] 通过率 > 90%

### 5.3 前端测试
```bash
cd ../frontend
npm test
```
- [ ] 测试开始运行
- [ ] 83/83 测试通过
- [ ] 无错误

---

## 第六阶段：功能验证

### 6.1 启动后端服务
```bash
# 确保虚拟环境已激活
cd backend
python app.py
```
- [ ] 服务启动成功
- [ ] 显示: Running on http://localhost:5000
- [ ] 无错误信息

### 6.2 启动前端服务（新终端）
```bash
cd frontend
npm run dev
```
- [ ] 服务启动成功
- [ ] 显示: Local: http://localhost:3000
- [ ] 无错误信息

### 6.3 访问应用
- [ ] 打开浏览器访问 http://localhost:3000
- [ ] 页面正常加载
- [ ] 无控制台错误

---

## 第七阶段：最终确认

### 7.1 文件完整性检查
- [ ] `backend/requirements.txt` 存在
- [ ] `backend/requirements-freeze.txt` 存在
- [ ] `frontend/package.json` 存在
- [ ] `INSTALLATION_GUIDE.md` 存在
- [ ] `QUICK_SETUP.md` 存在
- [ ] `VERSION_VERIFICATION.md` 存在

### 7.2 环境信息记录
```bash
# Python 版本
python --version

# pip 版本
pip --version

# Node 版本
node --version

# npm 版本
npm --version
```
- [ ] 所有版本信息已记录

### 7.3 创建环境快照（可选）
```bash
# 后端依赖快照
cd backend
pip freeze > my-requirements-freeze.txt

# 前端依赖快照
cd ../frontend
npm list --depth=0 > my-package-list.txt
```
- [ ] 快照已创建

---

## 🎉 安装完成确认

### 全部检查项统计
- 总检查项: 约 60 项
- 必需项: 约 45 项
- 可选项: 约 15 项

### 最终确认
- [ ] Python 3.10.11 已安装
- [ ] 虚拟环境已创建并激活
- [ ] 后端依赖已安装（20+ 包）
- [ ] 前端依赖已安装（400+ 包）
- [ ] PaddleOCR 可正常导入
- [ ] NumPy 版本 < 2.0
- [ ] 后端测试通过
- [ ] 前端测试通过
- [ ] 后端服务可启动
- [ ] 前端服务可启动

---

## ⚠️ 常见问题快速修复

### 问题 1: Python 版本不对
```bash
# 检查版本
py -3.10 --version

# 如果不是 3.10.11，重新安装 Python 3.10.11
```

### 问题 2: PaddleOCR 安装失败
```bash
# 使用国内镜像
pip install paddlepaddle==2.6.2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install paddleocr==2.7.0.3 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题 3: NumPy 版本冲突
```bash
# 强制安装正确版本
pip install "numpy>=1.24.3,<2.0" --force-reinstall
```

### 问题 4: 虚拟环境激活失败（Windows）
```powershell
# 如果 PowerShell 报错，使用 CMD
.\venv310\Scripts\activate.bat
```

### 问题 5: 测试失败
```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 清除缓存
pip cache purge
```

---

## 📞 获取帮助

如果遇到问题：

1. 查看 `INSTALLATION_GUIDE.md` 详细说明
2. 查看 `VERSION_VERIFICATION.md` 版本信息
3. 查看 `QUICK_SETUP.md` 快速命令
4. 检查 Python 版本是否为 3.10.11
5. 确认使用了国内镜像源（如果在中国）

---

## 📝 安装记录

**安装日期**: _______________

**安装人**: _______________

**Python 版本**: _______________

**操作系统**: _______________

**安装时间**: _______________ 分钟

**遇到的问题**: 

_______________________________________________

_______________________________________________

**解决方案**: 

_______________________________________________

_______________________________________________

---

**文档版本**: 1.0
**最后更新**: 2026-01-18
**维护者**: Kiro AI Assistant
