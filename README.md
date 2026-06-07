# 美团本地活动规划比赛版 Demo

一个基于 `FastAPI + React + 高德/Mock 双模式` 的本地短时活动规划与执行 Agent，面向比赛提交与本地运行演示。

当前版本覆盖以下主流程：

- 一句话目标输入
- 多轮对话澄清需求（`/chat` + `/chat/stream`）
- 家庭/朋友场景结构化理解
- 对话阶段直接产出结构化 `Goal`
- 显式展示已识别需求标签与规划阶段
- 真实本地 POI 检索或 Mock 降级
- 4-6 小时主/备方案编排与统一评分对比
- 路线与通勤时长展示
- 确认后一键推进关键执行动作
- 失败补偿与分享结果输出

## 目录结构

```text
.
├─ api.py
├─ pyproject.toml
├─ design.md
├─ frontend
│  └─ src
│     ├─ App.tsx
│     ├─ App.css
│     ├─ index.css
│     └─ main.tsx
└─ meituan_demo
   ├─ agent.py
   ├─ executor.py
   ├─ mock_tools.py
   ├─ models.py
   ├─ parser.py
   ├─ planner.py
   └─ share.py
```

## 运行方式

### 0. 一键启动

在项目根目录执行：

```powershell
.\start-local.ps1
```

脚本会自动完成这些事情：

- 构建前端静态资源
- 启动后端：`http://127.0.0.1:8002/`
- 启动前端预览：`http://127.0.0.1:4175/`
- 固定前端只连接 `8002` 后端
- 启动前检查 `LLM` 和高德相关环境变量，并提示缺失项

推荐先配置这些变量再执行：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek Key"
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
$env:AMAP_WEB_SERVICE_KEY="你的高德 Web Service Key"
$env:VITE_AMAP_JS_KEY="你的高德 JS Key"
.\start-local.ps1
```

### 1. 启动后端

```bash
python -m uvicorn api:app --reload --host 127.0.0.1 --port 8002
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run preview
```

前端默认请求 `http://127.0.0.1:8002`，如需修改可设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8002
```

## 高德接入

### 后端真实本地能力

后端通过 `AMAP_WEB_SERVICE_KEY` 调用高德 Web Service API：

```bash
$env:AMAP_WEB_SERVICE_KEY="你的高德 Web Service Key"
python -m uvicorn api:app --reload --host 127.0.0.1 --port 8002
```

### 前端地图展示

前端通过 `VITE_AMAP_JS_KEY` 加载高德 JS API：

```bash
cd frontend
$env:VITE_AMAP_JS_KEY="你的高德 JS Key"
npm run preview
```

默认地址固定为：

- 前端：`http://127.0.0.1:4175/`
- 后端：`http://127.0.0.1:8002/`

## 双模式说明

- 有 `AMAP_WEB_SERVICE_KEY`：
  - `/plan` 优先使用真实高德能力检索附近活动、餐饮和路线
- 有 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`：
  - `/chat`、`/chat/stream` 优先使用 LLM 生成自然回复，并回传结构化 `goal`
- 无 `AMAP_WEB_SERVICE_KEY`：
  - 自动回退到现有 Mock 候选，保证比赛演示不会中断
- 无 LLM Key、模型异常或网络失败：
  - 不再回退到固定规则答复，前端直接提示服务器或网络异常
- 无 `VITE_AMAP_JS_KEY`：
  - 页面仍可展示文本路线和地点卡片，只是不显示真实地图

## 对话与规划主路径

- 当前默认主路径：
  - 前端通过 `/chat/stream` 做流式需求澄清
  - 当 `ready_to_plan=true` 且返回结构化 `goal` 后，前端优先走 `/plan/direct`
  - 仅当 `goal` 缺失或 `direct plan` 失败时，才回退到 `/plan` 文本规划
- 这样做的目的：
  - 减少“对话理解”和“规划消费”之间的信息损耗
  - 保证比赛演示时家庭/朋友双场景都能更稳定地产生差异化方案

## 默认演示建议

- 家庭场景：
  - `今天下午想和老婆孩子从公司附近出发玩几个小时，别太远，孩子5岁，顺便吃得清淡一点`
- 朋友场景：
  - `今天下午想和4个朋友出去玩和吃饭，别太折腾，最好能聊天`

建议比赛演示时：
- 开启浏览器定位，围绕当前城市附近生成方案
- 优先展示真实本地模式
- 保留 Mock 降级作为网络或 Key 异常时的 fallback

## Demo 说明

- 当前版本是“比赛版进行中”：
  - 已有比赛级 Web 单页骨架
  - 已支持真实高德数据接入与 Mock 降级
  - 已支持 `LLM 优先 + 规则兜底` 的对话澄清
  - 已支持流式对话、改口、冲突提示、无效输入处理和复述确认
  - 已支持主/备方案、路线摘要、执行状态和分享文案
  - 已支持需求标签、阶段进度、评分依据、推荐理由和主备方案对比
- 执行层仍以模拟执行为主，重点验证“从推荐到任务推进”的闭环
- CLI 仍可保留为开发或应急演示路径，但比赛主路径为 Web

## 当前版本新增亮点

- 解释性更强：
  - 前端会展示需求标签、规划阶段、评分拆解和推荐理由
  - 评委可以直接看到“为什么推荐这条，而不是备选”
- 更贴近老师反馈里的比赛要求：
  - 不只展示结果，还展示“怎么抽标签、怎么评分、怎么对比”
  - 更适合后续答辩说明“我们的规划逻辑和说服力”
- 更接近对话式体验：
  - 输入区保留一句话入口和预设场景
  - 结果区按“识别需求 -> 筛选本地供给 -> 对比主备方案 -> 执行”展开

## 异常场景演示

可通过环境变量 `MEITUAN_DEMO_SCENARIO` 切换不同 Mock 异常场景：

- `normal`：正常闭环
- `activity_unavailable`：首选活动不可用，自动回退备选方案
- `restaurant_busy`：餐厅排队时间变长
- `availability_timeout`：可用性检查超时
- `reserve_timeout`：预约动作失败，触发补偿重试
- `partial_failure`：排号或配送失败，触发补偿动作

示例：

```bash
$env:MEITUAN_DEMO_SCENARIO="partial_failure"
python app.py "今天下午想和4个朋友出去玩和吃饭，别太折腾"
```

## 设计文档

- 设计说明见 `design.md`
