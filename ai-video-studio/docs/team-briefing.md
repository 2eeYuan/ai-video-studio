# AI 视频创作工作台 — 团队开发任务书

## 一、项目概述

**一句话描述**：一个普通人也能用的 AI 视频创作桌面应用，输入主题即可自动生成短视频。

**技术栈**：Tauri 2（Rust 后端 + React 前端）+ Python Sidecar（视频生成引擎）

**参考产品**：即梦（字节跳动的 AI 视频创作工具）

**当前进度**：基础框架已搭建完成（可运行），需要在此基础上迭代开发。

---

## 二、已有成果

以下模块已完成基础实现，代码在 `D:\test_agent\myMovie\ai-video-studio`：

| 模块 | 状态 | 说明 |
|------|------|------|
| 项目骨架 | ✅ 完成 | Tauri 2 + React + Python 三层架构 |
| 前端 UI | ✅ 完成 | 三栏工作台布局（脚本/素材/字幕 + 视频预览） |
| LLM 脚本生成 | ✅ 完成 | 输入主题 → AI 生成文案 + 搜索关键词 |
| 素材拼接模式 | ✅ 完成 | Pexels 搜索 → 下载 → FFmpeg 合成 |
| TTS 语音合成 | ✅ 完成 | Edge TTS 中文语音 |
| 字幕生成 | ✅ 完成 | 自动 SRT 字幕 |
| 设置页面 | ✅ 完成 | LLM/TTS/Pexels 配置 |
| 桌面打包 | ✅ 完成 | Windows .exe 可运行 |

---

## 三、开发任务清单

### 优先级说明
- 🔴 P0：核心功能，必须完成
- 🟡 P1：重要功能，影响用户体验
- 🟢 P2：增强功能，可后续迭代

---

### 任务 1：Agent 编排系统 🔴 P0

**目标**：实现即梦式的多阶段 Agent 工作流

**具体工作**：
1. 在 Python sidecar 中实现 `Orchestrator` 类，管理以下阶段流转：
   ```
   创意方向选择 → 剧本创作 → 风格探索 → 素材生成 → 分镜设计 → Prompt 生成 → 视频生成 → 合成
   ```
2. 每个阶段是一个独立的 Agent（参考 `docs/agent-harness-design.md` 第 2 节）
3. 实现用户确认点机制：每个阶段完成后暂停，等待用户确认再继续

**产出文件**：
- `sidecar/services/agents/orchestrator.py`
- `sidecar/services/agents/director.py`
- `sidecar/services/agents/script_writer.py`
- `sidecar/services/agents/storyboard_designer.py`

**验收标准**：
- 输入"末世囤货"→ AI 给出 4 个方向选择 → 用户选择后自动生成剧本 → 确认后生成分镜表

---

### 任务 2：结构化 Prompt 系统 🔴 P0

**目标**：实现即梦式的素材映射 + 镜头级 Prompt 生成

**具体工作**：
1. 实现素材映射表机制：
   ```
   @图片1 = 公寓客厅清晨 (apartment_livingroom_realistic_film)
   @图片2 = 陈峰 (chenfeng_character_main)
   ```
2. 实现标准化分镜表输出（JSON schema）：
   ```json
   {
     "shot_id": "1-1",
     "shot_type": "特写",
     "angle": "平视",
     "description": "画面描述",
     "sound": "声音描述",
     "camera_movement": "固定",
     "duration": 3
   }
   ```
3. 实现视频 Prompt 生成器：将分镜表转换为 AIGC 视频 Prompt

**产出文件**：
- `sidecar/services/agents/prompt_generator.py`
- `sidecar/services/schemas/` (JSON schema 定义)

**验收标准**：
- 生成的 Prompt 包含素材引用（`@[图片1]`）
- 每个镜头有景别、角度、运镜、时长、声音

---

### 任务 3：Director Agent（创意方向选择）🔴 P0

**目标**：实现即梦式的"先给选项，再深入"模式

**具体工作**：
1. 实现 Director Agent，输入主题，输出 3-4 个创意方向
2. 每个方向包含：风格标签 + 核心概念 + 场景描述
3. 前端实现选择 UI（卡片式选择界面）

**系统 Prompt 设计**：
```
你是一个专业的短视频创意总监。根据用户主题，构思 4 个不同方向的创意。
每个方向必须有明显的差异性，不要给出微调变体。
```

**产出文件**：
- `sidecar/services/agents/director.py`
- `src/components/workspace/DirectionSelector.tsx`

**验收标准**：
- 输入"末世囤货"→ 输出 4 个方向（日常风/幽默风/紧张型/废土风）
- 用户点击选择后进入下一阶段

---

### 任务 4：AIGC 素材生成集成 🟡 P1

**目标**：连接即梦 API，实现 AI 生成视频/图片素材

**具体工作**：
1. 完善 Dreamina adapter，实现完整的 text2video / image2video 流程
2. 实现素材生成的进度跟踪
3. 实现"先生成风格参考图 → 用户选择 → 批量生成所有素材"的流程

**产出文件**：
- `sidecar/services/aigc/dreamina.py`（完善）
- `sidecar/services/aigc/kling.py`（新增）

**验收标准**：
- 输入提示词 → 生成视频片段 → 可预览
- 支持即梦和 Kling 两种 AIGC 工具

---

### 任务 5：素材匹配优化 🟡 P1

**目标**：素材拼接模式下，让素材与旁白内容对应

**具体工作**：
1. 实现"按脚本顺序匹配"模式（MoneyPrinterTurbo 已有此功能）
2. 根据每个段落的关键词分别搜索素材
3. 素材裁剪：根据旁白时长自动裁剪素材片段

**产出文件**：
- `sidecar/services/material_service.py`（增强）
- `sidecar/services/video_service.py`（增强）

**验收标准**：
- 旁白讲到"超市被抢空"时，画面正好是空货架

---

### 任务 6：设置持久化 🟡 P1

**目标**：用户配置的 API Key 等信息持久保存

**具体工作**：
1. 使用 Tauri Store 插件保存设置
2. 首次启动时引导用户配置 LLM 和 Pexels API Key
3. 配置保存后自动启动 Python sidecar

**产出文件**：
- `src-tauri/src/commands/settings.rs`
- `src/components/settings/SettingsDialog.tsx`（增强）

---

### 任务 7：Python Sidecar 自动管理 🟡 P1

**目标**：应用启动时自动管理 Python sidecar 进程

**具体工作**：
1. 将 Python sidecar 打包为独立可执行文件（PyInstaller）
2. Tauri 启动时自动启动 sidecar 进程
3. 应用退出时自动关闭 sidecar

**产出文件**：
- `sidecar/build.spec`（PyInstaller 配置）
- `src-tauri/src/sidecar/mod.rs`（增强）

---

### 任务 8：视频预览优化 🟢 P2

**目标**：更好的视频预览体验

**具体工作**：
1. 视频预览播放器支持全屏
2. 视频时间线显示字幕预览
3. 支持导出为不同分辨率/格式

---

### 任务 9：国际化 🟢 P2

**目标**：支持中英文界面

**具体工作**：
1. 补全 i18n 翻译文件
2. 设置页面添加语言切换
3. Python sidecar 的错误信息也做国际化

---

## 四、技术决策要点

### 4.1 为什么用 Python Sidecar 而不是纯 Rust？

| 方案 | 优点 | 缺点 |
|------|------|------|
| 纯 Rust | 性能好，单文件分发 | 重写成本高，MoviePy 无 Rust 替代 |
| Python Sidecar | 复用成熟代码，开发快 | 需要 Python 环境，分发复杂 |
| PyInstaller 打包 | 单文件分发 | 包体大（~100MB） |

**决策**：先用 Python Sidecar 开发，后续用 PyInstaller 打包为独立 exe。

### 4.2 LLM 供应商如何选择？

**决策**：不在代码里绑定任何 LLM。通过设置页面让用户自选，支持 OpenAI 兼容的所有供应商（DeepSeek、MiMo、Moonshot 等）。

### 4.3 素材拼接 vs AIGC 生成如何选择？

**决策**：两种模式并存，用户可在界面上切换：
- **快速模式**（素材拼接）：适合批量生产，3 分钟出片
- **精品模式**（AIGC 生成）：适合高质量需求，10-30 分钟出片

---

## 五、开发排期建议

| 周次 | 任务 | 产出 |
|------|------|------|
| 第 1 周 | 任务 1（Agent 编排）+ 任务 3（Director） | 可交互的多阶段工作流 |
| 第 2 周 | 任务 2（结构化 Prompt）+ 任务 5（素材匹配） | 分镜表 + 视频 Prompt 自动生成 |
| 第 3 周 | 任务 4（AIGC 集成）+ 任务 6（设置持久化） | AIGC 生成可用 |
| 第 4 周 | 任务 7（Sidecar 打包）+ 任务 8/9（优化） | 可分发的桌面应用 |

---

## 六、关键文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| Agent Harness 设计 | `docs/agent-harness-design.md` | Agent 类型、Prompt 模板、阶段编排 |
| 项目结构 | 项目根目录 | 已有代码的完整结构 |
| 即梦 CLI 参考 | `refs/即梦 CLI 体验指南.md` | 即梦 API 的使用方式 |
| MoneyPrinterTurbo | `refs/MoneyPrinterTurbo/` | 素材拼接模式的参考实现 |
