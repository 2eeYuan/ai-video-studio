# Coding Agent 任务清单

## 背景

先通读以下两个文档理解产品逻辑：
- `docs/workflow-logic.md` — 五阶段流程和数据流
- `docs/agent-harness-design.md` — Agent 设计原理

核心理念：文生视频大模型已进入音视频一体化时代（豆包等），AIGC 生成视频时自带音频，不需要单独 TTS。

---

## 任务 1：修复 AI创作 → 分镜 的断点

**文件：** `src/components/workspace/AgentWorkflow.tsx`

**问题：** `handleConfirmScript` 调用的是 `agentApi.submitStoryboard()`，但分镜生成逻辑在 `orchestrator.submit_script()` 中。Storyboard Agent 从未被触发。

**修复：**
1. `handleConfirmScript` 应先调 `agentApi.submitScript(taskId)` 触发分镜 Agent
2. 等返回结果后再自动进入 storyboard 阶段
3. 用户在 StoryboardViewer 中确认后，再调 `agentApi.submitStoryboard(taskId)`

---

## 任务 2：分镜数据传递给流水线

**文件：** `src/components/workspace/WorkspaceLayout.tsx`

**问题：** `handleAgentStartPipeline` 只提取旁白文本，丢弃分镜数据。

**修复：**
1. WorkspaceLayout 新增共享 state：`shots`（分镜数组）
2. `handleAgentStartPipeline` 将完整的 `storyboard.shots` 传入 `shots` state
3. 每个 shot 的结构：`{ shot_id, shot_type, description, narration, duration }`

---

## 任务 3：AIGC 标签页接通分镜表

**文件：** `src/components/workspace/MaterialPanel.tsx`

**问题：** AIGC 标签是死胡同，不读取分镜数据。

**修复：**
1. MaterialPanel 接收 `shots` prop（从 WorkspaceLayout 传入）
2. 遍历 shots，每个镜头显示：画面描述 + 旁白文本 + 时长
3. 对每个镜头调用 sidecar 的 AIGC 生成接口
4. 生成完成后显示视频预览缩略图
5. 支持单个镜头重新生成
6. 生成时的 prompt = `description + " " + narration`（音视频一体）

---

## 任务 4：字幕标签页接通流水线

**文件：** `src/components/workspace/SubtitlePanel.tsx`

**问题：** 所有控件的 onChange 是空函数，设置不传递。

**修复：**
1. 所有控件改为受控组件，状态提升到 WorkspaceLayout
2. WorkspaceLayout 新增共享 state：`subtitleConfig` 和 `bgmConfig`
3. 传递给 VideoPreview，由 VideoPreview 传给流水线

---

## 任务 5：重构流水线 — 按分镜逐镜头生成

**文件：** `sidecar/services/pipeline_service.py`

**问题：** 当前流水线按 3 个关键词生成通用片段，还保留了无用的 TTS 和关键词生成步骤。

**修复：**
1. `run_pipeline` 新增参数：`shots: list[dict]`（分镜数组）
2. 删除 Step 1（脚本生成）、Step 2（关键词生成）、Step 3（TTS）
3. Step 5 改为：遍历 shots，对每个 shot 调用 `adapter.text2video(description + narration, duration=shot.duration, ratio=aspect)`
4. Step 6/7/8 保留：拼接 → 字幕 → 输出
5. 如果 shots 为空，fallback 到旧逻辑（兼容模式）

---

## 任务 6：移除 TTS 相关代码

**涉及文件：**
- `sidecar/main.py` — PipelineRequest 删除 tts 相关字段
- `sidecar/services/pipeline_service.py` — 删除 TTS 调用
- `src-tauri/src/lib.rs` — ai_start_pipeline 删除 tts 参数
- `src-tauri/src/sidecar/mod.rs` — start_pipeline 删除 tts 参数
- `src/lib/api/index.ts` — startPipeline 删除 tts 参数
- `src/components/workspace/VideoPreview.tsx` — 删除 TTS 设置加载

**注意：** settings 里的 TTS 配置面板可以保留（作为高级选项），但流水线不再使用它。

---

## 执行顺序

按以下顺序执行，每完成一个任务验证编译：

1. 任务 1（修复 Agent 调用顺序）
2. 任务 2（分镜数据传递）
3. 任务 5（重构流水线）
4. 任务 6（移除 TTS）
5. 任务 3（AIGC 标签接通）
6. 任务 4（字幕标签接通）

每个任务完成后运行 `npx tsc --noEmit` 和 `cargo check` 验证编译。
