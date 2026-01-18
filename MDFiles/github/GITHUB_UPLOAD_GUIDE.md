# GitHub 上传指南

本指南将帮助你将项目上传到 GitHub。

## 步骤 1：初始化 Git 仓库

在项目根目录执行：

```bash
git init
```

## 步骤 2：添加所有文件

```bash
git add .
```

## 步骤 3：创建第一次提交

```bash
git commit -m "Initial commit: PDF to Editable Web Layout System"
```

## 步骤 4：在 GitHub 上创建仓库

1. 打开 [GitHub](https://github.com)
2. 点击右上角的 "+" 按钮
3. 选择 "New repository"
4. 填写仓库信息：
   - **Repository name**: `pdf-to-editable-web` (或你喜欢的名字)
   - **Description**: `A system that converts scanned PDF documents into structured, editable web content using OCR`
   - **Public/Private**: 选择公开或私有
   - **不要**勾选 "Initialize this repository with a README"（我们已经有了）
5. 点击 "Create repository"

## 步骤 5：连接到远程仓库

GitHub 会显示一个页面，复制 "…or push an existing repository from the command line" 下的命令。

通常是这样的格式（替换 `YOUR_USERNAME` 和 `YOUR_REPO_NAME`）：

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### 示例

如果你的 GitHub 用户名是 `wanghuilin`，仓库名是 `pdf-to-editable-web`：

```bash
git remote add origin https://github.com/wanghuilin/pdf-to-editable-web.git
git branch -M main
git push -u origin main
```

## 步骤 6：输入 GitHub 凭证

第一次推送时，系统会要求你输入 GitHub 凭证：

### 使用 Personal Access Token (推荐)

1. 在 GitHub 上生成 Personal Access Token：
   - 进入 Settings → Developer settings → Personal access tokens → Tokens (classic)
   - 点击 "Generate new token (classic)"
   - 选择权限：至少勾选 `repo`
   - 生成并复制 token（只显示一次！）

2. 推送时：
   - Username: 你的 GitHub 用户名
   - Password: 粘贴你的 Personal Access Token

### 或使用 SSH (更方便)

如果你已经配置了 SSH 密钥，可以使用 SSH URL：

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

## 步骤 7：验证上传

访问你的 GitHub 仓库页面，应该能看到所有文件已经上传成功！

## 后续更新

以后如果要更新代码到 GitHub：

```bash
# 查看修改的文件
git status

# 添加修改的文件
git add .

# 提交修改
git commit -m "描述你的修改"

# 推送到 GitHub
git push
```

## 常见问题

### 问题 1：推送失败 - 认证错误

**解决方案**：使用 Personal Access Token 而不是密码。

### 问题 2：文件太大

**解决方案**：检查 `.gitignore` 是否正确配置，确保不上传：
- `node_modules/`
- `uploads/`
- `temp/`
- `.hypothesis/`
- 日志文件

### 问题 3：想要排除某些文件

编辑 `.gitignore` 文件，添加你想排除的文件或目录。

## 建议的仓库设置

上传后，建议在 GitHub 上：

1. **添加 Topics**（标签）：
   - `ocr`
   - `pdf-processing`
   - `editorjs`
   - `paddleocr`
   - `python`
   - `javascript`

2. **添加 Description**：
   ```
   A system that converts scanned PDF documents into structured, editable web content using OCR and Editor.js
   ```

3. **设置 About**：
   - Website: 如果你部署了在线版本
   - Topics: 添加相关标签

4. **创建 Release**（可选）：
   - 标记为 v1.0.0
   - 添加发布说明

## 需要帮助？

如果遇到问题，可以：
1. 检查 Git 状态：`git status`
2. 查看远程仓库：`git remote -v`
3. 查看提交历史：`git log --oneline`

祝你上传顺利！🚀
