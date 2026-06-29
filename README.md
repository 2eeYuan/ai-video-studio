# AI Video Studio

**Language:** [English](#english) | [中文](#中文)

<a id="english"></a>

## English

AI Video Studio is a desktop-first AI video production workspace that helps turn an idea into a structured video project.
It combines a Tauri + React interface with Python sidecar services for script writing, storyboard planning, material management, AIGC video generation, subtitles, text-to-speech, and final assembly.

### What It Does

- Guides a video concept from direction selection to script, storyboard, prompts, clips, subtitles, and export.
- Uses agent-style services for planning, writing, visual generation, review, and revision.
- Provides a desktop UI for managing project materials, generated shots, subtitles, preview, and workflow progress.
- Supports configurable AIGC providers through adapter-style services.
- Includes a separate Python pipeline package for event-driven multi-agent video generation experiments.

### Repository Layout

```text
.
+-- ai-video-studio/        # Tauri + React desktop application
|   +-- src/                # Frontend UI
|   +-- src-tauri/          # Tauri shell and Rust integration
|   +-- sidecar/            # Python sidecar services
+-- src/mymovie/            # Python multi-agent video pipeline
+-- docs/                   # Architecture notes
+-- config.yaml             # Pipeline configuration template
+-- pyproject.toml          # Python package metadata
```

### Quick Start

#### Desktop App

```bash
cd ai-video-studio
pnpm install
pnpm dev
```

#### Python Pipeline

```bash
pip install -e .
python -m mymovie.main
```

Set required API keys in your environment before running generation workflows.

[切换到中文](#中文)

---

<a id="中文"></a>

## 中文

AI Video Studio 是一个面向桌面端的 AI 视频生产工作台，用来把一个创意逐步推进成结构化的视频项目。
它将 Tauri + React 界面与 Python sidecar 服务结合，覆盖剧本创作、分镜规划、素材管理、AIGC 视频生成、字幕、配音和最终合成。

### 核心能力

- 从创意方向、剧本、分镜、Prompt、视频片段、字幕到导出，串联完整视频制作流程。
- 使用 Agent 风格服务处理策划、写作、视觉生成、审核和修改。
- 提供桌面 UI 管理项目素材、生成镜头、字幕、预览和工作流进度。
- 通过适配器式服务支持不同 AIGC 视频生成提供方。
- 包含独立的 Python 流水线包，用于事件驱动的多 Agent 视频生成实验。

### 仓库结构

```text
.
+-- ai-video-studio/        # Tauri + React 桌面应用
|   +-- src/                # 前端界面
|   +-- src-tauri/          # Tauri 外壳与 Rust 集成
|   +-- sidecar/            # Python sidecar 服务
+-- src/mymovie/            # Python 多 Agent 视频流水线
+-- docs/                   # 架构说明
+-- config.yaml             # 流水线配置模板
+-- pyproject.toml          # Python 包元数据
```

### 快速开始

#### 桌面应用

```bash
cd ai-video-studio
pnpm install
pnpm dev
```

#### Python 流水线

```bash
pip install -e .
python -m mymovie.main
```

运行生成流程前，请先在环境变量中配置所需 API Key。

[Switch to English](#english)
