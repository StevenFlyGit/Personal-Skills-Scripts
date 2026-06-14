# Personal Skills & Scripts

主要存放因方便个人开发或学习流程而编写的 Agents 的 Skills 和 Scripts 脚本。

# 仓库简介

本仓库用于集中管理我在个人开发、自动化处理和学习实践过程中编写的 Skills 与 Scripts。内容主要围绕 GitHub 仓库初始化、Notion 内容处理等场景，目标是提升重复性工作的效率，并沉淀可复用的自动化流程。

# 项目概览

本仓库目前包含两个主要 Skill：

## 1. `github-repo-setup`

用于自动化 GitHub 仓库初始化与同步流程，主要能力包括：

- 创建远程 GitHub 仓库
- 初始化或克隆本地 Git 仓库
- 生成基础 `README.md`，避免编码或乱码问题
- 添加标准 `.gitignore`
- 将本地代码推送到远程仓库

### 相关脚本

- `github-repo-setup/scripts/setup_repo.py`

### 使用前准备

- 配置环境变量 `GITHUB_PERSONAL_ACCESS_TOKEN`
- 使用具备仓库创建权限的 GitHub Fine-grained PAT

### 使用示例

```powershell
python scripts/setup_repo.py setup --repo-name "My-New-Project" --description "A sample project" --local-path "E:\ProgrameSpace\MyProject" --output "result.json"
```

### 适用场景

- 新项目仓库初始化
- 本地项目快速同步到 GitHub
- 为新仓库生成基础工程结构

## 2. `notion-latex-converter`

用于处理 Notion 页面中的 LaTeX 公式内容，主要能力包括：

- 将 Notion 页面中的行内公式与块级公式转换为原生 LaTeX equation objects
- 支持按指定标题下的内容进行转换
- 支持对整页内容进行转换
- 提供校验与审计功能，用于检查未转换公式或乱码问题

### 相关脚本

- `notion-latex-converter/latex_converter.py`

### 使用前准备

- 安装依赖：`requests`
- 配置环境变量 `NOTION_TOKEN`
- 确保目标 Notion 页面已分享给对应 Integration

### 使用示例

按标题转换：

```bash
python latex_converter.py convert <page_id> <heading_name>
```

转换整页：

```bash
python latex_converter.py convert <page_id> ALL
```

按标题校验：

```bash
python latex_converter.py verify <page_id> <heading_name>
```

校验整页：

```bash
python latex_converter.py verify <page_id> ALL
```

### 适用场景

- 批量整理 Notion 数学公式
- 将文本公式迁移为 Notion 原生公式块
- 检查页面内容是否存在乱码或未处理公式

# 目录说明

```text
Personal-Skills-Scripts/
├── github-repo-setup/
│   ├── SKILL.md
│   └── scripts/
│       └── setup_repo.py
├── notion-latex-converter/
│   ├── SKILL.md
│   └── latex_converter.py
└── README.md
```

# 快速开始

如果你想先体验仓库中的能力，建议优先查看各目录下的 `SKILL.md` 文件，它们分别说明了对应 Skill 的用途、依赖、参数和使用方式。

# 功能特性

- 面向个人开发与学习流程的自动化脚本集合
- 覆盖 GitHub 仓库创建、同步与基础配置
- 覆盖 Notion 公式转换与内容审计
- 具备重试机制与基础限流处理，增强脚本稳定性

# 常见问题

## 1. Notion 页面未共享

若页面未共享给 Notion Integration，脚本可能无法访问目标页面。

## 2. 环境变量未配置

请先确认已正确设置：

- `GITHUB_PERSONAL_ACCESS_TOKEN`
- `NOTION_TOKEN`

## 3. 权限不足

GitHub Token 需要具备仓库创建相关权限；Notion Token 需要有访问目标页面的权限。

# 说明

本仓库内容主要面向个人使用场景，可根据后续新增的 Skills 或 Scripts 持续扩展。
