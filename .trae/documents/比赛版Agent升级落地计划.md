# 比赛版 Agent 升级落地计划

## Summary
- 目标：在现有 `Python FastAPI + React Vite + Mock Agent` 基线上，升级为适合比赛提交与现场运行演示的“本地短时活动规划与执行 Agent”作品。
- 主线：优先补强真实本地能力，其次完成比赛级 Web 展示，再增强执行可信度与答辩表达。
- 关键约束：开发者白天上课、无法保证每天投入；比赛版必须支持提交完整代码后本地运行演示；真实本地能力优先采用高德能力接入。
- 成功标准：
  - 用户可通过 Web 页面一句话输入需求并获得真实本地候选与路线时长。
  - 系统可稳定展示主方案、备选方案、地图/路线、执行状态、分享结果。
  - 在无真实交易能力时，规划和本地供给尽量真实，执行层支持真实 Key 模式与 Mock 降级模式。
  - 项目始终保留可运行版本，便于分阶段推进和中断恢复。

## Current State Analysis
### 已存在的实现
- 后端入口：[api.py](file:///d:/美团AI/api.py)
  - 已提供 `POST /plan` 与 `POST /execute`
  - 使用 `FastAPI + Pydantic`
  - 已接入 CORS，能被前端直接调用
- Agent 主体：[agent.py](file:///d:/美团AI/meituan_demo/agent.py)
  - 已串联 parser、planner、executor、share
- 规划与执行能力：
  - [parser.py](file:///d:/美团AI/meituan_demo/parser.py)：已支持家庭/朋友场景解析
  - [planner.py](file:///d:/美团AI/meituan_demo/planner.py)：已支持主备方案、评分、时长控制、动作生成
  - [executor.py](file:///d:/美团AI/meituan_demo/executor.py)：已支持失败补偿
  - [mock_tools.py](file:///d:/美团AI/meituan_demo/mock_tools.py)：当前仍是本地 Mock 数据和 Mock 执行
- 前端基础：[App.tsx](file:///d:/美团AI/frontend/src/App.tsx)
  - 已有基本输入框、规划请求、执行请求、结果展示
  - 当前为单页雏形，尚未接入地图，也没有比赛级信息架构
- 项目说明：
  - [README.md](file:///d:/美团AI/README.md)：当前仍以 CLI/Mock Demo 为主
  - [design.md](file:///d:/美团AI/design.md)：说明的是当前 Mock 版设计，而非比赛版路线

### 明显缺口
- 缺真实本地数据能力：尚未接地图、POI、路线、时间矩阵
- 缺比赛级前端展示：当前页面仅展示文本结果，没有地图、本地感、执行状态面板与更完整的叙事
- 缺真实/降级双模式设计：虽然已有环境变量场景，但没有“真实 Key 模式 + 无 Key 兜底模式”的明确工程结构
- 缺比赛导向文档：现有设计说明仍偏 Demo 说明，未完全对齐创新性、完整性、应用效果、商业价值四个评审维度

## Assumptions & Decisions
- 地图与本地数据优先采用高德方案，API Key 由用户提供，通过本地环境变量注入。
- 比赛演示主路径为：提交完整代码后，本地启动前后端并运行演示。
- 默认演示案例优先围绕当前城市附近场景设计，而不是纯通用虚拟案例。
- 当前不把“真实交易全闭环”作为第一目标；优先实现“真实检索与路线 + 可控执行闭环”。
- 现有 `FastAPI` 后端与 `React + Vite` 前端继续保留，不重做技术栈。
- CLI 保留为开发/兜底演示路径，但比赛主展示路径切换为 Web。

## Proposed Changes
### Phase 1: 真实本地能力接入
#### 目标
- 将现有 `MockToolbox` 升级为“真实高德能力 + Mock 回退”的统一数据层。

#### 计划修改的文件
- [mock_tools.py](file:///d:/美团AI/meituan_demo/mock_tools.py)
  - What：拆分为查询适配层，区分真实本地检索与现有 Mock 数据
  - Why：当前所有候选都是写死的，无法满足比赛对应用效果和真实本地能力的要求
  - How：保留现有 Mock 数据逻辑，新增高德查询接口封装；根据是否存在 API Key 进入真实模式或降级模式
- [planner.py](file:///d:/美团AI/meituan_demo/planner.py)
  - What：将候选评分从“只基于本地标签”扩展为“真实距离/时间 + 标签 + 可用性”
  - Why：只有真实路线后，“离家不远”和 4-6 小时时长约束才有说服力
  - How：引入通勤时长、区域距离、真实 POI 信息作为评分输入
- [models.py](file:///d:/美团AI/meituan_demo/models.py)
  - What：扩充候选与站点字段
  - Why：当前字段不足以承载真实 POI、经纬度、商圈、通勤时间、数据来源
  - How：增加 `lat/lng`、`poi_id`、`travel_minutes`、`source`、`business_area` 等必要字段
- [parser.py](file:///d:/美团AI/meituan_demo/parser.py)
  - What：补充出发点、当前位置、当前城市等上下文入口
  - Why：真实本地检索需要明确搜索中心点或城市
  - How：在不破坏现有自然语言解析的前提下，增加默认位置上下文与后续 UI 传参支持
- [api.py](file:///d:/美团AI/api.py)
  - What：扩展 `plan` 请求模型，支持位置、城市、出行方式等输入
  - Why：Web 页面需要把地图和本地上下文传给后端
  - How：新增兼容字段，保持旧请求体仍可运行

#### 工程要求
- 采用“双模式”：
  - 有 Key：真实高德能力
  - 无 Key：回退到当前 Mock 逻辑
- 每次改动后仍保证 `/plan` 和 `/execute` 可运行

### Phase 2: 比赛版 Web UI 重构
#### 目标
- 将当前前端雏形升级为适合比赛演示的单页应用。

#### 计划修改的文件
- [App.tsx](file:///d:/美团AI/frontend/src/App.tsx)
  - What：重构页面结构
  - Why：当前页面只适合基础结果展示，不足以支撑完整性与应用效果
  - How：调整为输入区、结构化约束区、主/备方案区、执行状态区、分享结果区
- [App.css](file:///d:/美团AI/frontend/src/App.css)
  - What：移除模板残留样式，建立比赛版页面样式
  - Why：当前样式仍有大量 Vite 模板遗留，不匹配当前业务
  - How：围绕信息卡片、时间线、状态面板、双栏布局重写
- [index.css](file:///d:/美团AI/frontend/src/index.css)
  - What：统一全局基础样式与主题
  - Why：当前仅有最小样式定义，不足以支撑完整页面
  - How：补充页面底色、字体、间距、卡片层级等基础 token
- [main.tsx](file:///d:/美团AI/frontend/src/main.tsx)
  - What：仅在必要时调整全局挂载结构
  - Why：保持入口简单，但为地图脚本与全局状态留足空间
  - How：不做复杂状态库引入，优先保持轻量

#### 页面结构决策
- 第一屏必须同时出现：
  - 一句话输入
  - 位置/城市上下文
  - “生成规划”按钮
- 规划结果区必须展示：
  - 主推荐方案
  - 至少 1 条备选方案
  - 每段时间、地点、时长、理由
- 执行结果区必须展示：
  - 动作进度
  - 成功/失败
  - 补偿动作
  - 分享文案

### Phase 3: 地图与路线展示
#### 目标
- 在前端展示真实本地感，而不只是文本结果。

#### 计划修改的文件
- [App.tsx](file:///d:/美团AI/frontend/src/App.tsx)
  - What：加入地图组件容器与路线信息卡
  - Why：没有地图时，真实本地能力很难被评委直接感知
  - How：优先展示地点标注与路线摘要，地图容器与文本路线同时存在
- [api.py](file:///d:/美团AI/api.py)
  - What：返回前端所需的经纬度、POI 信息、路线摘要
  - Why：前端地图渲染与路线展示需要结构化数据
  - How：确保返回结果字段对前端友好，而不是直接裸回 dataclass 结构

#### 展示策略
- 地图是加分项，但不能成为唯一信息来源
- 即使地图脚本加载失败，页面仍要能展示路线文本、地点卡片和通勤时间

### Phase 4: 执行可信度与异常兜底增强
#### 目标
- 把执行闭环从“演示逻辑”提升为“可信任务推进”。

#### 计划修改的文件
- [executor.py](file:///d:/美团AI/meituan_demo/executor.py)
  - What：增强执行状态与补偿动作语义
  - Why：当前已支持补偿，但前后端都还不够像“真实执行过程”
  - How：补充状态阶段、失败类型、补偿链条、用户可理解说明
- [share.py](file:///d:/美团AI/meituan_demo/share.py)
  - What：优化分享文案结构
  - Why：比赛中分享结果是闭环的最后一击，需要更自然且更像真正可转发内容
  - How：按家庭/朋友场景分模板生成
- [api.py](file:///d:/美团AI/api.py)
  - What：返回更明确的执行摘要与状态字段
  - Why：前端需要渲染时间线式执行过程，而不是只渲染结果数组
  - How：引入兼容结构，避免破坏当前执行接口

### Phase 5: 比赛材料与运行稳定性
#### 目标
- 让项目满足“提交代码后可直接运行演示”的要求。

#### 计划修改的文件
- [README.md](file:///d:/美团AI/README.md)
  - What：改成比赛版启动说明
  - Why：当前 README 仍偏 CLI/Mock 说明，不够指导评审或队友运行
  - How：明确前后端启动、环境变量、Key 配置、降级模式、默认案例
- [design.md](file:///d:/美团AI/design.md)
  - What：升级为比赛版设计说明
  - Why：当前文档没有充分体现真实本地能力、比赛评审标准与产品价值
  - How：围绕创新性、完整性、应用效果、商业价值重写结构
- [requirements.txt](file:///d:/美团AI/requirements.txt)
  - What：补充后端真实接入所需依赖
  - Why：当前依赖过少，不足以覆盖比赛版运行能力
  - How：只加入确实使用的依赖，避免过度扩展
- [frontend/package.json](file:///d:/美团AI/frontend/package.json)
  - What：如确需引入地图或 UI 库，再最小化补依赖
  - Why：维持可运行与易安装优先
  - How：避免大规模引入状态管理或重型图表库

## Delivery Sequence
### 第一周：真实本地能力
- 完成高德接入抽象
- 打通位置、POI、路线、时长
- 保留 Mock 降级

### 第二周：Web 主界面与地图展示
- 完成比赛版页面结构
- 打通主/备方案和地图/路线
- 形成可稳定演示的主路径

### 第三周：执行可信度、文档与答辩表达
- 增强执行状态与补偿展示
- 完善设计文档与 README
- 准备默认案例和商业价值表达

### 截止前缓冲
- 集中做稳定性验证
- 准备无 Key / 网络波动 fallback
- 预演比赛运行流程

## Verification Steps
- 后端验证
  - `/plan` 在真实 Key 模式和 Mock 降级模式都能返回结果
  - `/execute` 在两种模式下都能稳定返回执行摘要
- 前端验证
  - `frontend` 本地 dev 模式可正常请求后端
  - 页面能展示主方案、备选方案、地图/路线摘要、执行结果、分享文案
  - 地图加载失败时仍能完成文本级展示
- 体验验证
  - 家庭场景和朋友场景至少各有一个默认案例
  - “离家不远”与 4-6 小时约束在真实路线下可解释
  - 失败补偿能被清晰看见，不会静默失败
- 比赛运行验证
  - 全部代码从零安装后可启动
  - 环境变量说明清晰
  - 无 Key 时能切换到降级模式，不阻断整体演示
