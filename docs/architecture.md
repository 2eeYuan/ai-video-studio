# mymovie 项目运行详解

本文档按照一个视频项目从启动到完成的完整运行顺序，详细介绍系统的每个组件如何协作。

---

## 一、系统总览

mymovie 是一个全自动 AI 视频生产流水线。用户只需给出一个主题（如"赤壁之战"），系统就会自动完成：对话策划 → 资料搜集 → 剧本编写 → 分镜脚本 → AIGC Prompt 生成 → 视频分段生成 → 拼接 → 审核 → 反馈修改，直到用户满意为止。

### 核心架构：事件驱动多 Agent

系统由 **11 个并发运行的组件** 组成，它们通过一个 **消息总线（MessageBus）** 传递消息，彼此不直接调用：

```
┌─────────────────────────────────────────────────────────────────┐
│                         MessageBus                              │
│              (asyncio.Queue 发布/订阅路由器)                      │
├─────────┬──────────┬──────────┬──────────┬──────────┬───────────┤
│Dialog   │Research  │Script    │Storyboard│Prompt    │Segment    │
│Agent    │Agent     │Agent     │Agent     │Agent     │Agent      │
├─────────┼──────────┼──────────┼──────────┼──────────┼───────────┤
│VideoGen │Assembly  │Review    │Revision  │          │           │
│Agent    │Agent     │Agent     │Agent     │Orchestrator          │
└─────────┴──────────┴──────────┴──────────┴───────────────────────┘
```

### 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 异步框架 | asyncio |
| LLM | mimo 2.5 pro（Anthropic 兼容 API） |
| AIGC 视频生成 | 即梦 CLI（dreamina），可插拔适配器 |
| 视频拼接 | FFmpeg |
| CLI 美化 | rich |
| 配置 | YAML + 环境变量 |

---

## 二、启动流程

### 命令行入口

用户在终端执行：

```bash
python -m mymovie.new "赤壁之战" --adapter dreamina --duration 120
```

### main.py 做了什么

`src/mymovie/main.py` 的 `main()` 函数是整个程序的入口点，它依次完成以下工作：

**第 1 步：加载配置**

```python
config = load_config()  # 读取 config.yaml，解析 ${MIMO_API_KEY} 等环境变量
```

`config.py` 中的 `load_config()` 读取 `config.yaml`，递归替换所有 `${VAR}` 格式的环境变量，返回一个 `AppConfig` 对象，包含：
- `llm` — LLM 的 endpoint、API key、model ID、temperature 等
- `adapters` — AIGC 工具配置（默认用 dreamina，轮询超时 60 秒，最多重试 3 次）
- `video` — 视频参数（默认时长 60 秒、分段 5/10 秒、比例 16:9、分辨率 720P、FFmpeg 拼接方式）
- `projects` — 项目产物存放目录（默认 `./projects`）

**第 2 步：创建项目目录**

```python
project_name = args.topic.replace(" ", "_")[:50]  # "赤壁之战"
project_dir = Path("./projects") / "赤壁之战"
project_dir.mkdir(parents=True, exist_ok=True)
```

**第 3 步：初始化 LLM 客户端**

```python
llm = LLMClient(config.llm)
```

`utils/llm.py` 中的 `LLMClient` 封装了 `anthropic.AsyncAnthropic`，指向 mimo 的 endpoint `https://token-plan-cn.xiaomimimo.com/anthropic`。它提供三个方法：
- `chat(system, user)` — 单轮对话，返回文本
- `chat_json(system, user)` — 单轮对话，要求 LLM 返回 JSON，自动解析为 dict，失败时重试
- `chat_messages(system, messages)` — 多轮对话，传入历史消息列表

所有方法内置 **3 次重试 + 指数退避**，处理 429 限流、500 服务器错误和网络超时。

**第 4 步：创建消息总线**

```python
bus = MessageBus()
```

`bus/bus.py` 中的 `MessageBus` 是整个系统的神经中枢。它维护一个字典：

```python
_subscribers: dict[MessageType, list[asyncio.Queue]]
```

当某个 Agent 调用 `bus.register("agent_name", [MessageType.X, MessageType.Y])` 时，总线为它创建一个 `asyncio.Queue`，并把这个 Queue 注册到对应的消息类型下。之后任何组件调用 `bus.publish(message)` 时，总线会把消息复制到所有订阅了该类型的 Queue 中。

**第 5 步：注册 AIGC 适配器**

```python
adapter_registry = AdapterRegistry()
adapter_registry.register(DreaminaAdapter(config.adapters.dreamina))
```

`adapters/registry.py` 中的 `AdapterRegistry` 是一个简单的名称→适配器映射表。当前只注册了 `DreaminaAdapter`，以后要加可灵、Runway 等工具，只需实现 `AIGCAdapter` 接口并注册即可。

`adapters/dreamina.py` 中的 `DreaminaAdapter` 通过 `asyncio.create_subprocess_exec` 调用 `dreamina` 命令行工具，封装了：
- `text2video(prompt, duration, ratio, resolution)` — 调用 `dreamina text2video --prompt=... --duration=5 --poll=30`
- `text2image(prompt, ratio, resolution)` — 调用 `dreamina text2image`
- `image2video(image_path, prompt, duration)` — 调用 `dreamina image2video`
- `query_result(handle)` — 调用 `dreamina query_result --submit_id=...`
- `download(handle, dest_dir)` — 下载生成结果到本地

**第 6 步：创建所有 Agent 和 Orchestrator**

```python
dialog_agent = DialogAgent(bus, llm, args.topic)
research_agent = ResearchAgent(bus, llm)
scriptwriter_agent = ScriptwriterAgent(bus, llm)
storyboard_agent = StoryboardAgent(bus, llm)
prompt_agent = PromptAgent(bus, llm)
segmentation_agent = SegmentationAgent(bus, max_duration=10)
video_gen_agent = VideoGenAgent(bus, adapter_registry, default_adapter="dreamina", max_retries=3)
assembly_agent = AssemblyAgent(bus, config.video.ffmpeg, project_dir)
review_agent = ReviewAgent(bus)
revision_agent = RevisionAgent(bus, llm)
orchestrator = Orchestrator(bus, context)
```

每个 Agent 都持有 `bus` 的引用（用于收发消息），部分 Agent 还持有 `llm`（用于调用大模型）或 `adapter_registry`（用于调用 AIGC 工具）。

**第 7 步：启动所有 Agent 为并发 asyncio.Task**

```python
tasks = [
    asyncio.create_task(orchestrator.start(), name="orchestrator"),
    asyncio.create_task(dialog_agent.start(), name="dialog"),
    asyncio.create_task(research_agent.start(), name="research"),
    # ... 其余 8 个 Agent
]
```

每个 Agent 的 `start()` 方法（定义在 `agents/base.py`）做了同样的事情：
1. 调用 `bus.register(self.name, self.subscribed_types())` 注册自己关心的消息类型，获得一个 Queue
2. 进入无限循环：`while True: msg = await queue.get(); responses = await self.handle(msg)`
3. 对 `handle()` 返回的每条回复消息，调用 `bus.publish(r)` 发布出去
4. 如果 `handle()` 抛出异常，自动发布一条 `AGENT_ERROR` 消息

**第 8 步：触发流水线启动**

```python
orchestrator.kick_off()  # 将状态从 IDLE 切换到 DIALOG
await bus.publish(Message(type=MessageType.PIPELINE_START, payload={"topic": "赤壁之战"}, sender="main"))
```

这条 `PIPELINE_START` 消息被发布到总线上，DialogAgent 订阅了它，于是 DialogAgent 被唤醒，开始工作。

---

## 三、流水线运行顺序

以下是系统从头到尾的完整运行流程，每一步都标注了 **哪个 Agent 在工作**、**它读取什么输入**、**产出什么输出**、**发布了什么消息**。

### 阶段 1：对话策划（DialogAgent）

**触发**：收到 `PIPELINE_START` 消息

**做了什么**：
1. 将用户的主题（如"赤壁之战"）发送给 LLM，附带 system prompt（定义在 `prompts/dialog_system.txt`）："你是一个专业的视频策划导演..."
2. LLM 返回第一个问题，如："你想讲赤壁之战的哪个阶段？是战前的谋略博弈，还是火烧连营的高潮？"
3. 问题通过 `print()` 输出到终端，同时发布 `DIALOG_TURN` 消息
4. Orchestrator 收到 `DIALOG_TURN` 后再次发布 `DIALOG_TURN`，DialogAgent 被唤醒，等待用户输入
5. 用户在终端输入回答，DialogAgent 将回答发送给 LLM
6. LLM 判断信息是否足够：
   - 如果不够：返回下一个问题，循环继续
   - 如果足够：回复中包含 `READY_TO_FINALIZE` 标记
7. 用户也可以随时输入 `/done` 强制结束对话

**结束时**：DialogAgent 要求 LLM 将所有对话内容整理为结构化的 `StoryBrief` JSON，包含：
- `topic` — 主题
- `genre` — 类型（历史剧、科幻短片等）
- `setting` — 时代和地点
- `characters` — 角色列表（名字、外貌、性格、角色定位）
- `tone` — 基调（史诗、黑暗、喜剧等）
- `target_duration_seconds` — 目标时长
- `visual_style` — 视觉风格（电影感、动漫、写实等）

然后发布 `STORY_DETAILS_READY` 消息，payload 中携带 `story_brief`。

**产物**：`StoryBrief` 对象，保存在 `PipelineContext.story_brief`

---

### 阶段 2：资料搜集（ResearchAgent）

**触发**：Orchestrator 收到 `STORY_DETAILS_READY`，切换状态到 `RESEARCH`，发布 `RESEARCH_REQUEST`

**做了什么**：
1. 从消息 payload 中取出 `story_brief`
2. 将 StoryBrief JSON 发送给 LLM，附带 system prompt："你是一个专业的历史和文化研究员..."
3. LLM 返回相关的历史资料、人物背景、文化细节等

**输出**：`ResearchPack` 对象，包含：
- `topic` — 主题
- `items` — 资料条目列表，每条有 `title`、`content`、`source`
- `summary` — 整体总结

发布 `RESEARCH_COMPLETE` 消息。

**产物**：`ResearchPack`，保存在 `PipelineContext.research_pack`

---

### 阶段 3：剧本编写（ScriptwriterAgent）

**触发**：Orchestrator 收到 `RESEARCH_COMPLETE`，切换到 `SCRIPT`，发布 `SCRIPT_REQUEST`

**做了什么**：
1. 取出 `story_brief` 和 `research_pack`
2. 将两者 JSON 拼接后发给 LLM，附带 system prompt："你是一个专业的编剧..."
3. LLM 返回完整的剧本

**输出**：`Script` 对象，包含：
- `title` — 标题
- `synopsis` — 剧情梗概
- `scenes` — 场景列表，每个场景包含：
  - `scene_number` — 场景编号
  - `location` — 地点
  - `time_of_day` — 时间
  - `characters_present` — 在场角色
  - `action` — 行动描述（舞台指示）
  - `dialogue` — 对话列表（角色、台词、表演指示）
  - `estimated_duration_seconds` — 预估时长
  - `mood` — 氛围

发布 `SCRIPT_READY` 消息。

**产物**：`Script`，保存在 `PipelineContext.script`

---

### 阶段 4：分镜脚本（StoryboardAgent）

**触发**：Orchestrator 收到 `SCRIPT_READY`，切换到 `STORYBOARD`，发布 `STORYBOARD_REQUEST`

**做了什么**：
1. 取出 `script`
2. 将剧本 JSON 发给 LLM，附带 system prompt："你是一个专业的分镜师..."
3. LLM 将每个场景拆分为具体的镜头

**输出**：`Storyboard` 对象，包含：
- `shots` — 镜头列表，每个镜头包含：
  - `shot_number` — 镜头编号
  - `scene_ref` — 所属场景编号
  - `description` — 镜头描述（画面中发生什么）
  - `camera` — 运镜信息：
    - `type` — 类型（static/pan_left/pan_right/dolly_in/dolly_out/tracking/zoom_in/zoom_out）
    - `speed` — 速度（slow/medium/fast）
    - `start_frame` — 起始画面描述
    - `end_frame` — 结束画面描述
  - `duration_seconds` — 时长（5 或 10 秒）
  - `music_cue` — 音乐提示
  - `sound_effect` — 音效
  - `visual_notes` — 视觉风格备注（光线、色调等）
- `total_estimated_duration` — 总时长

发布 `STORYBOARD_READY` 消息。

**产物**：`Storyboard`，保存在 `PipelineContext.storyboard`

---

### 阶段 5：AIGC Prompt 生成（PromptAgent）

**触发**：Orchestrator 收到 `STORYBOARD_READY`，切换到 `PROMPT_GENERATION`，发布 `PROMPT_REQUEST`

**做了什么**：
1. 取出 `storyboard`
2. 将分镜脚本 JSON 发给 LLM，附带 system prompt："你是一个AIGC视频生成prompt专家..."
3. LLM 将每个镜头翻译为适合 AI 视频生成工具的文本 prompt

**输出**：`AIGCPrompt` 列表，每个包含：
- `shot_ref` — 对应的镜头编号
- `prompt_text` — AIGC prompt 文本（如："Cinematic wide shot of ancient Chinese battlefield at dawn, mist rising from the Yangtze River, war drums in the distance, camera slowly pushing in"）
- `negative_prompt` — 不希望出现的元素（如："text, watermark, blurry"）
- `suggested_duration` — 建议时长（5 或 10 秒）
- `tool_type` — "text2video" 或 "text2image"
- `visual_style_tags` — 风格标签

发布 `PROMPTS_READY` 消息。

**产物**：`list[AIGCPrompt]`，保存在 `PipelineContext.prompts`

---

### 阶段 6：视频分段（SegmentationAgent）

**触发**：Orchestrator 收到 `PROMPTS_READY`，切换到 `SEGMENTATION`，发布 `SEGMENTATION_REQUEST`

**做了什么**：
1. 取出 prompts 列表
2. 将每个 AIGCPrompt 转换为一个 `Segment`，根据 `suggested_duration` 确定时长（不足 7 秒用 5 秒，否则用 10 秒）

**输出**：`Segment` 列表，每个包含：
- `index` — 段落序号（在最终视频中的位置）
- `prompt` — AIGC prompt 文本
- `duration` — 时长（5 或 10 秒）
- `shot_refs` — 对应的镜头编号列表
- `video_path` — 生成后的视频文件路径（初始为 None）
- `status` — 状态（pending/generating/done/failed）
- `submit_id` — AIGC 任务 ID（生成后填充）
- `generation_attempts` — 已尝试次数
- `error_log` — 错误日志

发布 `SEGMENTS_READY` 消息。

**产物**：`list[Segment]`，保存在 `PipelineContext.segments`

---

### 阶段 7：视频生成（VideoGenAgent）

**触发**：Orchestrator 收到 `SEGMENTS_READY`，切换到 `VIDEO_GENERATION`，然后 **为每个 Segment 发布一条 `VIDEOGEN_REQUEST` 消息**

这是整个流水线中最耗时的阶段。VideoGenAgent 订阅了 `VIDEOGEN_REQUEST`，每收到一条就处理一个段落。

**对每个段落做了什么**：
1. 从消息 payload 中取出 `Segment` 对象
2. 根据 `segment.adapter_name` 从 `AdapterRegistry` 获取对应的 AIGC 适配器（默认是 DreaminaAdapter）
3. 调用适配器的 `text2video(prompt, duration)` 方法
4. DreaminaAdapter 内部执行：`dreamina text2video --prompt="..." --duration=5 --ratio=16:9 --video_resolution=720P --poll=30`
5. `--poll=30` 表示 CLI 会自动轮询 30 秒等待结果
6. 如果 CLI 返回了结果（视频 URL 或本地路径），调用 `download()` 下载到本地
7. 如果成功：发布 `VIDEOGEN_SEGMENT_DONE` 消息，payload 包含 `segment_index` 和 `video_path`
8. 如果失败：进入重试逻辑

**重试机制**：
- 每个段落最多尝试 3 次（`max_retries=3`）
- 第 1 次失败后等 5 秒，第 2 次失败后等 15 秒（指数退避：`5 * 2^attempt`）
- 3 次都失败：发布 `AGENT_ERROR` 消息，标记为不可恢复

**Orchestrator 如何知道所有段落都完成了**：
Orchestrator 在 `VIDEO_GENERATION` 状态下，每收到一条 `VIDEOGEN_SEGMENT_DONE`，就把对应的 `video_path` 存入 `PipelineContext.video_paths[segment_index]`。当所有段落都完成后（由外部逻辑判断），发布 `VIDEOGEN_ALL_DONE`。

**产物**：多个视频文件（`seg_000.mp4`、`seg_001.mp4`...），路径保存在 `PipelineContext.video_paths`

---

### 阶段 8：视频拼接（AssemblyAgent）

**触发**：Orchestrator 收到 `VIDEOGEN_ALL_DONE`，切换到 `ASSEMBLY`，发布 `ASSEMBLY_REQUEST`，payload 包含按顺序排列的视频路径列表

**做了什么**：
1. 取出有序的视频路径列表
2. 调用 `utils/ffmpeg.py` 中的 `concat_videos()` 函数
3. 默认使用 **demuxer 方式**拼接（快速，不重新编码）：
   ```
   ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy final.mp4
   ```
4. 如果 demuxer 失败（通常是编码格式不一致），自动回退到 **filter 方式**（较慢，但能处理不同格式）：
   ```
   ffmpeg -y -i seg0.mp4 -i seg1.mp4 -filter_complex "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]" -map [outv] -map [outa] -c:v libx264 -c:a aac final.mp4
   ```

**输出**：最终视频文件 `projects/赤壁之战/final.mp4`

发布 `ASSEMBLY_DONE` 消息，payload 包含 `output_path`。

**产物**：`final.mp4`，保存在 `PipelineContext.final_video_path`

---

### 阶段 9：用户审核（ReviewAgent）

**触发**：Orchestrator 收到 `ASSEMBLY_DONE`，切换到 `REVIEW`，发布 `REVIEW_REQUEST`

**做了什么**：
1. 在终端打印视频文件路径
2. 提示用户查看视频
3. 等待用户输入：
   - 输入 `ok` / `满意` / `done` → 发布 `PIPELINE_COMPLETE`，流水线结束
   - 输入其他内容 → 视为修改反馈，发布 `REVISION_REQUEST`

**这是一个交互式阶段**，系统会暂停等待用户输入。

---

### 阶段 10：反馈修改（RevisionAgent + 循环）

**触发**：Orchestrator 收到 `REVISION_REQUEST`，切换到 `REVISION`，将用户的反馈文本连同完整的上下文（剧本、分镜、当前段落列表）转发给 RevisionAgent

**RevisionAgent 做了什么**：
1. 将用户反馈 + 完整上下文发给 LLM，附带 system prompt："你是一个视频后期修改顾问..."
2. LLM 分析反馈，输出 `RevisionPlan`：
   - `segments_to_regenerate` — 需要重新生成的段落（索引 + 新 prompt + 原因）
   - `segments_to_add` — 需要新增的段落（插入位置 + prompt + 时长）
   - `segments_to_remove` — 需要删除的段落索引
   - `notes` — 给用户的修改说明

**Orchestrator 收到 `REVISION_SEGMENTS_READY` 后**：
1. 应用删除：从段落列表中移除指定段落
2. 应用新增：在指定位置插入新段落
3. 应用修改：更新指定段落的 prompt，状态改为 `pending`
4. 重新编号所有段落
5. 清除需要重新生成的段落的 video_path
6. 切换回 `VIDEO_GENERATION` 状态
7. **只为状态为 `pending` 的段落发送 `VIDEOGEN_REQUEST`**（已生成的段落不会重新生成）

然后流程回到 **阶段 7**，只重新生成需要修改的段落，再拼接，再审核，直到用户满意。

---

## 四、组件功能速查表

### 消息总线（bus/）

| 文件 | 功能 |
|------|------|
| `bus/message.py` | 定义 `MessageType` 枚举（24 种消息类型）和 `Message` 数据类（type, payload, sender, correlation_id, timestamp） |
| `bus/bus.py` | `MessageBus` — 基于 `asyncio.Queue` 的发布/订阅路由器。Agent 调用 `register()` 订阅消息类型，调用 `publish()` 发布消息 |

### 数据模型（models/）

| 文件 | 功能 |
|------|------|
| `models/story.py` | `StoryBrief`（故事概要）和 `CharacterDesc`（角色描述） |
| `models/research.py` | `ResearchPack`（资料包）和 `ResearchItem`（单条资料） |
| `models/script.py` | `Script`（剧本）、`Scene`（场景）、`DialogueLine`（对话行） |
| `models/storyboard.py` | `Storyboard`（分镜）、`Shot`（镜头）、`CameraMove`（运镜） |
| `models/prompt.py` | `AIGCPrompt`（AIGC 工具的 prompt） |
| `models/segment.py` | `Segment`（视频段落，包含状态追踪和错误日志） |
| `models/revision.py` | `RevisionPlan`（修改计划）、`SegmentRevision`、`SegmentAddition` |
| `models/pipeline.py` | `PipelineContext`（流水线上下文，累积所有产物）和 `PipelineState`（状态枚举）。支持 `save()`/`load()` 序列化为 JSON，实现断点续传 |

### Agent（agents/）

| Agent | 订阅消息 | 发布消息 | 功能 |
|-------|---------|---------|------|
| `DialogAgent` | PIPELINE_START, DIALOG_TURN | STORY_DETAILS_READY, DIALOG_TURN | 多轮对话确定故事细节，输出 StoryBrief |
| `ResearchAgent` | RESEARCH_REQUEST | RESEARCH_COMPLETE | 用 LLM 搜集背景资料，输出 ResearchPack |
| `ScriptwriterAgent` | SCRIPT_REQUEST | SCRIPT_READY | 用 LLM 编写完整剧本，输出 Script |
| `StoryboardAgent` | STORYBOARD_REQUEST | STORYBOARD_READY | 用 LLM 创建分镜脚本，输出 Storyboard |
| `PromptAgent` | PROMPT_REQUEST | PROMPTS_READY | 用 LLM 将分镜翻译为 AIGC prompt |
| `SegmentationAgent` | SEGMENTATION_REQUEST | SEGMENTS_READY | 将 prompt 按 5/10 秒分段 |
| `VideoGenAgent` | VIDEOGEN_REQUEST | VIDEOGEN_SEGMENT_DONE, VIDEOGEN_ALL_DONE, AGENT_ERROR | 调用 AIGC 适配器生成视频，带重试机制 |
| `AssemblyAgent` | ASSEMBLY_REQUEST | ASSEMBLY_DONE, AGENT_ERROR | 用 FFmpeg 拼接视频段落 |
| `ReviewAgent` | REVIEW_REQUEST | REVISION_REQUEST, PIPELINE_COMPLETE | 展示视频给用户，收集反馈 |
| `RevisionAgent` | REVISION_REQUEST | REVISION_SEGMENTS_READY | 用 LLM 分析反馈，生成修改计划 |

所有 Agent 继承 `agents/base.py` 中的 `BaseAgent` 抽象类。`BaseAgent.start()` 自动完成消息注册和循环处理，子类只需实现 `subscribed_types()` 和 `handle()`。

### AIGC 适配器（adapters/）

| 文件 | 功能 |
|------|------|
| `adapters/base.py` | `AIGCAdapter` 抽象基类（定义 text2video/text2image/image2video/query_result/download 接口）、`TaskHandle`（任务句柄）、`TaskResult`（任务结果）、`AIGCAdapterError`（异常） |
| `adapters/registry.py` | `AdapterRegistry` — 适配器注册表，按名称获取适配器 |
| `adapters/dreamina.py` | `DreaminaAdapter` — 即梦 CLI 的具体实现，通过 `asyncio.create_subprocess_exec` 调用 `dreamina` 命令 |

### Orchestrator（orchestrator/）

| 文件 | 功能 |
|------|------|
| `orchestrator/orchestrator.py` | 状态机，监听消息总线，根据当前状态和收到的消息类型执行状态转换。每次转换：存储产物 → 保存检查点 → 发布下一条触发消息 |

状态转换流程：
```
IDLE → DIALOG → RESEARCH → SCRIPT → STORYBOARD → PROMPT_GENERATION
→ SEGMENTATION → VIDEO_GENERATION → ASSEMBLY → REVIEW
                                              ↗
                              REVISION ←──────┘ (用户不满意)
                                 ↓
                          VIDEO_GENERATION (只重新生成修改的段落)
                                 ↓
                              ASSEMBLY → REVIEW (再次审核)
```

### 工具函数（utils/）

| 文件 | 功能 |
|------|------|
| `utils/llm.py` | `LLMClient` — 封装 Anthropic 兼容 API，支持 chat/chat_json/chat_messages，内置 3 次重试 |
| `utils/ffmpeg.py` | `concat_videos()` — FFmpeg 视频拼接，支持 demuxer（快速）和 filter（兼容）两种方式，demuxer 失败自动回退 filter |
| `utils/logger.py` | `setup_logging()` — 基于 rich 的日志配置 |

### System Prompts（prompts/）

| 文件 | 对应 Agent | 内容 |
|------|-----------|------|
| `dialog_system.txt` | DialogAgent | 视频策划导演的角色定义，指导如何通过对话收集故事信息 |
| `research_system.txt` | ResearchAgent | 历史/文化研究员的角色定义 |
| `scriptwriter_system.txt` | ScriptwriterAgent | 编剧的角色定义，规定剧本格式 |
| `storyboard_system.txt` | StoryboardAgent | 分镜师的角色定义，规定分镜格式 |
| `prompt_gen_system.txt` | PromptAgent | AIGC prompt 专家的角色定义 |
| `revision_system.txt` | RevisionAgent | 视频后期修改顾问的角色定义 |

---

## 五、配置文件（config.yaml）

```yaml
llm:
  base_url: "https://token-plan-cn.xiaomimimo.com/anthropic"  # mimo API endpoint
  api_key: "${MIMO_API_KEY}"        # 从环境变量读取
  model: "mimo-2.5-pro"             # 模型 ID
  max_tokens: 4096                  # 单次最大 token 数
  temperature: 0.7                  # 生成温度

adapters:
  default: "dreamina"               # 默认 AIGC 工具
  dreamina:
    download_dir: "./downloads"     # 视频下载目录
    poll_timeout: 60                # 轮询超时（秒）
    max_retries: 3                  # 最大重试次数

video:
  default_duration: 60              # 默认目标时长（秒）
  segment_durations: [5, 10]        # 支持的分段时长
  default_ratio: "16:9"             # 默认视频比例
  default_resolution: "720P"        # 默认分辨率
  ffmpeg:
    concat_method: "demuxer"        # 拼接方式（demuxer/filter）
    output_codec: "libx264"         # 输出编码
    output_format: "mp4"            # 输出格式

projects:
  base_dir: "./projects"            # 项目产物目录
```

---

## 六、断点续传机制

`PipelineContext` 在每次状态转换后自动调用 `save()`，将完整的流水线状态序列化为 `pipeline_state.json`：

```json
{
  "correlation_id": "a1b2c3d4e5f6",
  "state": "video_generation",
  "story_brief": { ... },
  "research_pack": { ... },
  "script": { ... },
  "storyboard": { ... },
  "prompts": [ ... ],
  "segments": [
    {"index": 0, "prompt": "...", "duration": 5, "status": "done", "video_path": "..."},
    {"index": 1, "prompt": "...", "duration": 10, "status": "pending", "video_path": null}
  ],
  "video_paths": {"0": "./projects/赤壁之战/segments/seg_000.mp4"},
  "final_video_path": null,
  "project_dir": "./projects/赤壁之战",
  "revision_count": 0
}
```

如果程序崩溃或用户中断（Ctrl+C），可以用以下命令恢复：

```bash
python -m mymovie.resume projects/赤壁之战/
```

`resume` 命令会：
1. 从 `pipeline_state.json` 加载 `PipelineContext`
2. 创建所有 Agent 和 Orchestrator
3. Orchestrator 从保存的状态继续运行（如从 `VIDEO_GENERATION` 恢复，继续生成未完成的段落）

---

## 七、错误处理

系统有三层防护：

### 第 1 层：段落级重试（VideoGenAgent）

每个视频段落最多尝试 3 次，指数退避（5s → 15s → 45s）：

```
段落 3 第 1 次失败 → 等 5 秒 → 第 2 次尝试
段落 3 第 2 次失败 → 等 15 秒 → 第 3 次尝试
段落 3 第 3 次失败 → 标记为 failed，发布 AGENT_ERROR
```

### 第 2 层：LLM 调用重试（LLMClient）

所有 LLM 调用内置 3 次重试，处理：
- 429 限流 → 等待后重试
- 500 服务器错误 → 等待后重试
- JSON 解析失败 → 重新提示 LLM 返回合法 JSON

### 第 3 层：流水线级错误处理（Orchestrator）

Orchestrator 监听所有 `AGENT_ERROR` 消息：
- `recoverable: True` → 记录日志，继续运行
- `recoverable: False` → 终止流水线

---

## 八、项目产物目录结构

一次完整运行后，项目目录如下：

```
projects/赤壁之战/
├── pipeline_state.json      # 流水线状态检查点
├── brief.json               # StoryBrief（故事概要）
├── research.json            # ResearchPack（研究资料）
├── script.json              # Script（剧本）
├── storyboard.json          # Storyboard（分镜脚本）
├── prompts.json             # AIGCPrompt 列表
├── segments.json            # Segment 列表
├── segments/                # 生成的视频段落
│   ├── seg_000.mp4
│   ├── seg_001.mp4
│   ├── seg_002.mp4
│   └── ...
└── final.mp4                # 最终拼接的完整视频
```

---

## 九、扩展：添加新的 AIGC 工具

系统的适配器模式使得添加新工具非常简单。以添加"可灵"为例：

1. 创建 `src/mymovie/adapters/kling.py`：

```python
class KlingAdapter(AIGCAdapter):
    name = "kling"

    async def text2video(self, prompt, duration, ratio="16:9", resolution="720P"):
        # 调用可灵的 API 或 CLI
        ...

    # 实现其他抽象方法...
```

2. 在 `main.py` 中注册：

```python
adapter_registry.register(KlingAdapter(config.adapters.kling))
```

3. 在 `config.yaml` 中添加配置：

```yaml
adapters:
  kling:
    api_key: "${KLING_API_KEY}"
    ...
```

之后用户可以通过 `--adapter kling` 选择使用可灵生成视频。
