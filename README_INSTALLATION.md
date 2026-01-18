# 安装文档导航

## 📚 文档概览

本项目提供了完整的安装文档体系，确保在任何电脑上都能顺利安装和运行。

---

## 🎯 快速开始

### 新手用户（第一次安装）
1. 阅读 **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - 详细的安装指南
2. 使用 **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - 逐项检查安装进度

### 有经验用户（快速安装）
1. 查看 **[QUICK_SETUP.md](QUICK_SETUP.md)** - 一键复制命令
2. 参考 **[VERSION_VERIFICATION.md](VERSION_VERIFICATION.md)** - 版本信息

---

## 📖 文档列表

### 核心安装文档

#### 1. [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) 📘
**用途**: 完整的安装指南  
**适合**: 第一次安装、详细了解安装过程  
**内容**:
- 系统要求
- 详细安装步骤
- 常见问题排查
- 启动项目指南
- 版本兼容性矩阵

**何时使用**: 
- ✅ 第一次在新电脑上安装
- ✅ 遇到安装问题需要排查
- ✅ 需要了解版本兼容性

---

#### 2. [QUICK_SETUP.md](QUICK_SETUP.md) ⚡
**用途**: 快速安装参考卡  
**适合**: 有经验的用户、快速安装  
**内容**:
- 一键复制的安装命令
- 关键版本信息
- 快速启动命令
- 常见错误快速修复

**何时使用**:
- ✅ 已经熟悉安装流程
- ✅ 需要快速复制命令
- ✅ 快速查看版本信息

---

#### 3. [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) ✅
**用途**: 安装检查清单  
**适合**: 确保安装完整、逐步验证  
**内容**:
- 60+ 项检查清单
- 分阶段验证
- 问题快速修复
- 安装记录表

**何时使用**:
- ✅ 需要确保每一步都正确
- ✅ 团队协作安装
- ✅ 记录安装过程

---

#### 4. [VERSION_VERIFICATION.md](VERSION_VERIFICATION.md) 🔍
**用途**: 版本验证报告  
**适合**: 确认版本、排查兼容性问题  
**内容**:
- 所有依赖版本清单
- 版本调整记录
- 兼容性矩阵
- 依赖关系树

**何时使用**:
- ✅ 确认安装的版本是否正确
- ✅ 排查版本冲突问题
- ✅ 了解版本调整原因

---

### 参考文档

#### 5. [DEPENDENCY_INSTALLATION_COMPLETE.md](DEPENDENCY_INSTALLATION_COMPLETE.md) 📊
**用途**: 安装完成报告  
**适合**: 了解安装历史、测试结果  
**内容**:
- 安装过程记录
- 测试结果统计
- 已知问题说明
- 下一步工作建议

---

#### 6. [PYTHON_VERSION_COMPATIBILITY_ANALYSIS.md](PYTHON_VERSION_COMPATIBILITY_ANALYSIS.md) 🐍
**用途**: Python 版本兼容性分析  
**适合**: 选择 Python 版本、了解兼容性  
**内容**:
- 各 Python 版本支持情况
- 详细的兼容性矩阵
- 推荐版本及理由
- 版本选择指南

---

### 配置文件

#### 7. [backend/requirements.txt](backend/requirements.txt) 📦
**用途**: 后端依赖清单（精简版）  
**内容**: 20 个直接依赖，版本已固定  
**使用**:
```bash
pip install -r backend/requirements.txt
```

---

#### 8. [backend/requirements-freeze.txt](backend/requirements-freeze.txt) 🔒
**用途**: 后端依赖完整快照  
**内容**: 106 个包（直接+间接依赖）  
**使用**: 用于完全复现环境
```bash
pip install -r backend/requirements-freeze.txt
```

---

## 🚀 安装流程图

```
开始
  ↓
选择文档
  ├─ 第一次安装 → INSTALLATION_GUIDE.md
  ├─ 快速安装 → QUICK_SETUP.md
  └─ 详细检查 → SETUP_CHECKLIST.md
  ↓
安装 Python 3.10.11
  ↓
创建虚拟环境
  ↓
安装后端依赖 (requirements.txt)
  ↓
验证核心组件
  ├─ PaddleOCR ✓
  ├─ NumPy < 2.0 ✓
  └─ 其他组件 ✓
  ↓
安装前端依赖
  ↓
运行测试
  ├─ 后端测试 ✓
  └─ 前端测试 ✓
  ↓
启动服务
  ├─ 后端服务 ✓
  └─ 前端服务 ✓
  ↓
完成 🎉
```

---

## 📋 关键版本信息

### Python 环境
```
Python: 3.10.11 (必需)
pip: 25.3+
虚拟环境: venv310
```

### 核心依赖
```
paddlepaddle: 2.6.2
paddleocr: 2.7.0.3
opencv-python: 4.6.0.66
numpy: 1.26.4 (必须 < 2.0)
Pillow: 10.1.0
PyMuPDF: 1.20.2
Flask: 3.0.0
```

---

## 🎯 使用场景指南

### 场景 1: 第一次在新电脑上安装
**推荐文档顺序**:
1. INSTALLATION_GUIDE.md（了解全流程）
2. SETUP_CHECKLIST.md（逐步执行）
3. VERSION_VERIFICATION.md（验证版本）

**预计时间**: 30-45 分钟

---

### 场景 2: 有经验的开发者快速安装
**推荐文档**:
1. QUICK_SETUP.md（复制命令）
2. VERSION_VERIFICATION.md（确认版本）

**预计时间**: 10-15 分钟

---

### 场景 3: 遇到安装问题
**推荐文档顺序**:
1. INSTALLATION_GUIDE.md（查看常见问题）
2. VERSION_VERIFICATION.md（检查版本）
3. QUICK_SETUP.md（快速修复命令）

---

### 场景 4: 团队协作安装
**推荐文档**:
1. SETUP_CHECKLIST.md（团队成员使用）
2. VERSION_VERIFICATION.md（技术负责人参考）

---

## ⚠️ 重要提示

### 必须遵守的规则
1. ❗ **Python 版本必须是 3.10.11**（或 3.9.13）
2. ❗ **不要使用 Python 3.12+**（PaddleOCR 不兼容）
3. ❗ **NumPy 必须 < 2.0**（OpenCV 要求）
4. ❗ **使用虚拟环境**（避免污染系统环境）

### 推荐做法
1. ✅ 使用国内镜像源（中国大陆）
2. ✅ 按照文档逐步执行
3. ✅ 每个阶段都进行验证
4. ✅ 记录遇到的问题和解决方案

---

## 🔧 快速命令参考

### 创建虚拟环境
```bash
# Windows
py -3.10 -m venv venv310
.\venv310\Scripts\Activate.ps1

# macOS/Linux
python3.10 -m venv venv310
source venv310/bin/activate
```

### 安装依赖
```bash
# 后端（使用国内镜像）
cd backend
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前端
cd frontend
npm install
```

### 验证安装
```bash
# 验证 PaddleOCR
python -c "import paddleocr; print('OK')"

# 运行测试
python -m pytest backend/tests/test_models.py -v
npm test
```

---

## 📞 获取帮助

### 文档内查找
1. 查看对应文档的"常见问题"部分
2. 查看 VERSION_VERIFICATION.md 的版本信息
3. 查看 INSTALLATION_GUIDE.md 的排查指南

### 问题排查顺序
1. 确认 Python 版本 = 3.10.11
2. 确认虚拟环境已激活
3. 确认 NumPy < 2.0
4. 查看错误信息并搜索文档
5. 尝试使用国内镜像源

---

## 📊 文档更新记录

| 日期 | 文档 | 更新内容 |
|------|------|---------|
| 2026-01-18 | 全部 | 初始版本，完整验证 |
| 2026-01-18 | requirements.txt | 更新版本号 |
| 2026-01-18 | requirements-freeze.txt | 生成完整快照 |

---

## ✅ 文档完整性检查

- [x] INSTALLATION_GUIDE.md - 详细安装指南
- [x] QUICK_SETUP.md - 快速参考卡
- [x] SETUP_CHECKLIST.md - 安装检查清单
- [x] VERSION_VERIFICATION.md - 版本验证报告
- [x] DEPENDENCY_INSTALLATION_COMPLETE.md - 安装完成报告
- [x] PYTHON_VERSION_COMPATIBILITY_ANALYSIS.md - 版本兼容性分析
- [x] backend/requirements.txt - 依赖清单
- [x] backend/requirements-freeze.txt - 完整快照
- [x] README_INSTALLATION.md - 本文件

---

## 🎉 开始安装

选择适合你的文档，开始安装吧！

**推荐**: 如果是第一次安装，从 [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) 开始。

---

**文档版本**: 1.0  
**最后更新**: 2026-01-18  
**维护者**: Kiro AI Assistant
