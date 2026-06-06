# Tasks
- [x] Task 1: 搭建 Demo 骨架与核心领域模型
  - [x] SubTask 1.1: 确定 Demo 形态（命令行或 Web UI）并建立本地启动入口
  - [x] SubTask 1.2: 定义 Goal、Constraint、Candidate、Itinerary、ExecutionAction、ExecutionResult 等核心数据结构
  - [x] SubTask 1.3: 建立 Agent 主流程骨架，串联“解析 -> 规划 -> 确认 -> 执行 -> 分享”

- [x] Task 2: 实现规划链路与评分策略
  - [x] SubTask 2.1: 实现自然语言目标解析，覆盖家庭和朋友两类场景
  - [x] SubTask 2.2: 实现候选活动、餐厅、补充活动的生成与过滤逻辑
  - [x] SubTask 2.3: 实现 4-6 小时行程编排与评分，输出主推荐方案和备选方案

- [x] Task 3: 实现 Tool 层与 Mock API
  - [x] SubTask 3.1: 实现活动检索、餐厅检索、可用性检查等查询类 Tool
  - [x] SubTask 3.2: 实现预约、排号、下单、配送、分享等执行类 Tool
  - [x] SubTask 3.3: 为全部 Tool 提供可复用的 Mock API 响应与异常注入能力

- [x] Task 4: 完成确认执行与失败兜底
  - [x] SubTask 4.1: 实现用户确认后的动作序列执行器
  - [x] SubTask 4.2: 实现资源不可用、工具超时、部分执行失败的降级与补偿逻辑
  - [x] SubTask 4.3: 输出逐项执行结果、替代建议与最终分享文案

- [x] Task 5: 补齐设计文档与演示说明
  - [x] SubTask 5.1: 编写不超过 2 页的设计文档，说明 Planning 策略、工具调用链路、异常处理机制
  - [x] SubTask 5.2: 确认 Demo 演示路径完整，能够展示规划、执行、分享闭环
  - [x] SubTask 5.3: 进行基础验证，确保关键场景可运行

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Task 2
- Task 4 depends on Task 3
- Task 5 depends on Task 2
- Task 5 depends on Task 3
- Task 5 depends on Task 4

# Parallelization Notes
- Task 2 与 Task 3 可在 Task 1 完成后并行推进
- Task 5.1 可在 Task 4 开始后同步整理，但最终内容以实际实现结果为准

# Milestone Roadmap
- [x] Milestone A: 已完成本地 Mock Demo 基线，具备可演示的规划、执行、分享闭环
- [x] Milestone B: 已补充比赛版后续推进原则，明确适配“白天上课、无法每天开发”的节奏
- [x] Milestone C: 已定义后续阶段优先级，按“真实本地能力 -> Web UI -> 执行增强 -> 体验打磨”推进

# Next Phase Queue
- Phase 1: 接入真实本地能力
  - Step 1.1: 选定并接入地图 API，完成定位、周边搜索、路线时长能力
  - Step 1.2: 用真实 POI 替换部分 Mock 候选，保留执行层 Mock 兜底
  - Step 1.3: 验证“离家不远”和总时长约束基于真实距离生效

- Phase 2: 建设比赛版 Web UI
  - Step 2.1: 搭建适合比赛展示的前端页面结构
  - Step 2.2: 展示主方案、备选方案、地图路线、执行状态和分享结果
  - Step 2.3: 保证无论中途暂停在哪个阶段，页面都能维持可运行版本

- Phase 3: 增强执行可信度
  - Step 3.1: 加入营业状态、排队、预约建议等准实时判断
  - Step 3.2: 增强执行结果、补偿动作和失败兜底展示
  - Step 3.3: 形成更接近比赛终版的完整演示路径

- Phase 4: 比赛前打磨与答辩准备
  - Step 4.1: 打磨交互文案、默认案例和演示稳定性
  - Step 4.2: 梳理亮点表达、对比价值和现场演示顺序
  - Step 4.3: 预留时间处理风险项和临场 fallback

# Time Strategy
- 每个 Phase 应拆成 1-3 次短时可完成的子任务，优先适配晚上或周末开发
- 每次结束都保留可运行版本，避免因课程安排造成中断成本过高
