# 比赛终版双场景 Agent 专业完善实施计划

## Summary
- 目标：在现有 `FastAPI + React + LLM/规则双轨对话 + 真实高德/Mock 双模式` 基础上，完善为一套适合比赛终版提交、现场稳定演示、并具备后续产品化基础的双场景本地活动规划 Agent。
- 范围：保留“家庭场景 + 朋友场景”双场景，重点完善对话澄清、结构化 Goal 直通规划、主备方案质量、执行可信度、前端对话体验、测试与演示稳定性。
- 路线决策：
  - 比赛终版优先，不以一次性做到真实生产上线为目标。
  - 双场景都保留，不先收敛到单场景 MVP。
  - 对话能力采用 `LLM 优先 + 规则引擎兜底`，保证效果与稳定性的平衡。
- 最终成功标准：
  - 用户通过自然对话，在家庭/朋友两类场景下都能稳定完成“澄清需求 -> 复述确认 -> 自动生成主备方案 -> 查看执行动作 -> 输出分享结果”闭环。
  - 对话阶段直接产出结构化 `Goal`，规划阶段优先走 `/plan/direct`，不再依赖文本兜底作为主路径。
  - 前端对话体验明显提升，支持流式回复、无效输入处理、改口、冲突提示、复述确认。
  - 项目具备比赛现场可运行、可恢复、可解释、可答辩的完整材料和验证路径。

## 当前状态分析
### 已有基础
- 后端已具备规划与执行主链路：
  - `api.py` 已提供 `/chat`、`/chat/stream`、`/plan`、`/plan/direct`、`/execute`。
  - `meituan_demo/agent.py` 已串联 parser、planner、executor、share。
  - `meituan_demo/planner.py` 已具备主备方案和评分逻辑。
  - `meituan_demo/executor.py` 已具备失败补偿的基本机制。
- 对话系统已进入“第二阶段”：
  - `meituan_demo/conversation.py` 已从简单追问器升级为规则状态机，支持寒暄、无效输入、改口检测、冲突检测、复述确认。
  - `meituan_demo/llm_conversation.py` 已开始支持 tool calling、SSE 流式输出、结构化 `goal` 回传。
- 前端已具备比赛版页面骨架：
  - `frontend/src/App.tsx` 已接入聊天、规划、执行和地图展示主流程。
  - `frontend/src/App.css` 已有较成熟的视觉系统、富文本消息样式、状态徽标和加载骨架。
- 测试开始建立：
  - `tests/test_conversation.py` 已覆盖改口、冲突、复述、小闲聊等状态机行为。
  - `tests/test_parser.py`、`tests/test_planner.py`、`tests/test_executor.py` 已覆盖解析、规划、执行主路径。

### 当前主要问题
- 对话主路径仍处于“新旧并存”状态：
  - `/plan/direct` 已新增，但前端仍保留 `plan_text` 相关旧路径，存在分叉。
  - 结构化 Goal 虽可从对话返回，但尚未成为唯一可信输入源。
- `LLMConversationEngine` 与 `ConversationOrchestrator` 的行为契约尚未完全统一：
  - 两者都能返回 `goal`，但未明确“优先谁、缺失时如何补、字段完整度如何校验”。
- 前端流式对话链路虽已接入，但尚未形成生产级稳健 UX：
  - 缺少严格的 SSE 异常分支处理、流终止保护、消息占位清理策略、重复触发保护。
- 对话富文本渲染采用手写 HTML 转换：
  - 适合 Demo，但需进一步收敛消息格式约定，避免样式和安全边界继续膨胀。
- 规划器仍主要消费 parser 语义，尚未围绕“对话产出的 Goal”做质量增强。
- 项目尚未形成“比赛终版”的验证闭环：
  - 现有测试偏单元级，缺 API 集成、对话-规划-执行联调、SSE 回归用例。
  - 文档虽有，但尚未形成“从启动到演示到答辩”的最终版运行指引。

### 多视角要求
- 用户视角：
  - 回复必须自然，不像表单，不重复，不自言自语。
  - 结果必须看得懂、信得过、可继续调整。
- 平台/运营视角：
  - 必须稳定可演示，有清晰 fallback，不因 Key、网络、地图脚本失败而整链路崩掉。
  - 默认案例、日志输出、异常路径都要可控。
- 评审视角：
  - 必须能看懂“为什么这样规划、为什么不是另一个备选、为什么这条链路可信”。
  - 需要清晰体现创新性、完整性、应用效果、商业价值。

## Assumptions & Decisions
- 本计划以“比赛终版可交付”为第一目标，不把真实交易系统打通作为当前阶段必达项。
- 保留双场景，不为了降低复杂度而砍掉朋友场景。
- 对话能力采用 `LLM 优先 + 规则兜底`：
  - 有可用模型和 Key 时，优先使用 `LLMConversationEngine`。
  - 模型不可用、超时或输出结构异常时，回退到 `ConversationOrchestrator`。
- 对话产出的结构化 `Goal` 作为后续演进的主路径输入。
- 保留 `/plan` 兼容旧文本路径，但将 `/plan/direct` 作为前端默认主路径。
- 采用 TDD 风格推进关键改动：对话状态机、Goal 契约、SSE、planner 适配等优先写失败测试。

## Proposed Changes
## Task 1: 统一对话输出契约，确立结构化 Goal 主路径
**目标：** 让“对话 -> Goal -> 规划”成为唯一明确主链路，减少旧的文本兜底分叉。

**文件：**
- 修改：`d:\美团AI\api.py`
- 修改：`d:\美团AI\frontend\src\App.tsx`
- 修改：`d:\美团AI\meituan_demo\conversation.py`
- 修改：`d:\美团AI\meituan_demo\llm_conversation.py`
- 测试：`d:\美团AI\tests\test_conversation.py`

**要做什么：**
- 明确 `ChatResponse` / SSE `done` 事件的稳定契约：
  - `assistant_reply`
  - `slots`
  - `ready_to_plan`
  - `suggested_replies`
  - `plan_text`
  - `goal`
- 规定 `ready_to_plan=true` 时必须满足：
  - `goal` 不为空
  - `goal.constraints` 完整
  - 关键字段齐全
- 前端优先使用 `goalFromChat` 走 `/plan/direct`，仅在异常回退时才走 `/plan` 文本路径。

**为什么：**
- 现在最大的不确定性不是功能缺失，而是链路有两套：一套文本兜底，一套结构化 Goal。继续并行会让后续修改越来越难收敛。

**怎么做：**
1. 在 `api.py` 中固定 chat 和 stream 的响应字段定义与注释。
2. 在 `conversation.py` 中把 `ready_to_plan` 的判定和 `goal` 构建绑死，不允许出现 ready 了但 goal 缺失。
3. 在 `llm_conversation.py` 中对 LLM tool output 做严格归一化：
   - `goal` 非 dict -> 置空
   - `goal` 缺关键字段 -> 置空并走 fallback
4. 在 `App.tsx` 中改造规划入口：
   - 默认 `goalFromChat -> /plan/direct`
   - 当 `goalFromChat` 缺失或 direct 失败时再退回 `/plan`
5. 为上述契约补测试，确保 ready 时必带 goal。

**验证：**
- 新增/更新测试覆盖：
  - `ready_to_plan=true` 时返回完整 `goal`
  - LLM 输出坏结构时能回退
  - 前端 direct plan 失败时能安全降级

## Task 2: 完善 LLM 优先 + 规则兜底的对话编排
**目标：** 把当前“有了状态机，但还不够稳定”的对话系统，升级成比赛终版可用的对话编排层。

**文件：**
- 修改：`d:\美团AI\meituan_demo\llm_conversation.py`
- 修改：`d:\美团AI\meituan_demo\conversation.py`
- 修改：`d:\美团AI\api.py`
- 测试：`d:\美团AI\tests\test_conversation.py`

**要做什么：**
- 补齐以下行为：
  - 改口后的明确确认
  - 冲突后的温和追问
  - 就绪后的自然复述确认
  - LLM 失败时自动回落规则引擎
  - 连续无效输入时不重复机械回答
- 统一 LLM 与规则引擎的“话术口径、字段语义、建议回复生成策略”。

**为什么：**
- 当前仓库里同时存在：
  - 一套规则状态机
  - 一套 LLM 流式引擎
- 如果行为契约不统一，后面会出现“同样一段输入，两种模式回复差异很大”的问题，比赛演示会非常不稳定。

**怎么做：**
1. 定义对话引擎统一行为清单：
   - 小闲聊
   - 无效输入
   - 改口
   - 冲突
   - ready 复述
   - 普通追问
2. 在 `llm_conversation.py` 中把 system prompt 精炼成可执行规范，减少模型自由发挥。
3. 在 `conversation.py` 中补足连续无效输入、重复追问去重和更自然的建议回复逻辑。
4. 在 `api.py` 的 stream endpoint 中明确错误事件格式，便于前端统一处理。
5. 用测试覆盖 LLM 降级规则引擎的等价行为。

**验证：**
- 单轮、双轮、多轮改口都能稳定通过。
- 无 Key / LLM 超时场景下，仍能给出完整可用回复。
- 家庭/朋友场景都能完成 ready 复述并返回结构化 goal。

## Task 3: 用对话产出的 Goal 反向增强 parser / planner 质量
**目标：** 不只是“能从对话产出 Goal”，还要让这个 Goal 真正提升规划质量和双场景适配度。

**文件：**
- 修改：`d:\美团AI\meituan_demo\parser.py`
- 修改：`d:\美团AI\meituan_demo\planner.py`
- 修改：`d:\美团AI\meituan_demo\models.py`（如确需补字段）
- 测试：`d:\美团AI\tests\test_parser.py`
- 测试：`d:\美团AI\tests\test_planner.py`

**要做什么：**
- 对齐 `Goal` 的来源与语义：
  - parser 路径与 conversation 路径生成的 Goal 含义一致
  - scene / group_size / duration / dining / pace / special_needs 解释一致
- 补强 planner 对以下信号的利用：
  - `pace_preference`
  - `special_needs`
  - `child_age_hint`
  - `travel_mode`
  - `distance_preference`
- 明确家庭/朋友双场景的差异化评分和 hard filter。

**为什么：**
- 如果对话产出了更好的 Goal，但 planner 仍按旧弱信号做规划，用户只会觉得“聊了很多，但结果没变好”。

**怎么做：**
1. 先补 parser 测试与 planner 测试，覆盖双场景关键偏好。
2. 明确 scene-specific 规则：
   - 家庭：安全、亲子友好、路线顺、节奏轻松优先
   - 朋友：社交氛围、可聊天、先玩后吃、时间衔接优先
3. 把 `special_needs` 细化为 planner 可消费标签，而不只是展示文本。
4. 如果发现 `Goal` 结构不够承载 planner 需要的信息，再最小化扩充 `models.py`。

**验证：**
- 同样的城市和时段下，家庭/朋友方案明显不同。
- 改变 `pace_preference`、`distance_preference` 后，主方案可观察变化。
- planner 测试能证明新字段确实影响排序和过滤。

## Task 4: 重构前端对话主路径，做成真正稳定的聊天式体验
**目标：** 让前端从“能展示对话”升级成“稳定、自然、可控的聊天产品界面”。

**文件：**
- 修改：`d:\美团AI\frontend\src\App.tsx`
- 修改：`d:\美团AI\frontend\src\App.css`
- 修改：`d:\美团AI\frontend\src\index.css`（如需要全局 token）

**要做什么：**
- 以 `/chat/stream` 为主，完善流式消息体验。
- 移除主路径上的遗留逻辑：
  - `plan_text` 旧兜底心智
  - 重复的 ready 提示逻辑
  - 聊天完成前后布局切换的不自然跳变
- 把当前聊天 UI 进一步打磨成：
  - 用户先说，AI 再回
  - 对话过程中不会突然掉到“系统面板感”
  - ready 后的方案生成过渡自然

**为什么：**
- 用户最强烈的反馈一直是“像自言自语、不像真人聊天”。这不是后端单点问题，前端呈现方式同样关键。

**怎么做：**
1. 在 `App.tsx` 中整理聊天数据流：
   - 用户消息
   - assistant 占位消息
   - token 累积
   - done 事件落状态
   - error 事件兜底
2. 对 `renderMessage()` 做收敛：
   - 限制支持的富文本语法
   - 避免继续膨胀为“自写 Markdown 引擎”
3. 调整 ready 态：
   - 对话收集完后不再出现割裂按钮墙
   - 方案生成中展示轻量 skeleton / thinking 状态
4. 调整错误态与空输入态：
   - 不把普通对话提示混进 error 面板
   - 无效输入走聊天引导，不走系统报错
5. 保留地图与结果展示，但保证“未出结果前仍是单列自然聊天感”。

**验证：**
- 家庭/朋友默认案例都能完整跑通聊天。
- SSE 中断、done 事件缺失、后端报错时前端不崩。
- 用户在聊天阶段不会看到明显的系统流程割裂。

## Task 5: 强化执行可信度与结果表达
**目标：** 把执行部分做得更像“可信任务推进”，而不是只是一串动作数组。

**文件：**
- 修改：`d:\美团AI\meituan_demo\executor.py`
- 修改：`d:\美团AI\meituan_demo\share.py`
- 修改：`d:\美团AI\api.py`
- 修改：`d:\美团AI\frontend\src\App.tsx`
- 测试：`d:\美团AI\tests\test_executor.py`

**要做什么：**
- 明确每个动作的：
  - 阶段名
  - 执行动机
  - 成功/失败原因
  - 补偿动作
  - 最终摘要
- 改进分享结果，让其更像真实可转发内容，而不是机械汇总。

**为什么：**
- 对评委和用户来说，执行层是“这个系统到底是不是只会推荐”的关键证明。

**怎么做：**
1. 在 executor 结果中规范 `details.stage`、`message`、`recovery_hint`。
2. 在前端执行状态卡里改成阶段式展示，不只是一串列表。
3. 在 `share.py` 中区分家庭/朋友输出模板：
   - 家庭版更强调节奏、孩子、吃饭安排、集合时间
   - 朋友版更强调氛围、先后安排、集合点
4. 为补偿链路补测试，确保场景异常下仍可解释。

**验证：**
- `partial_failure`、`reserve_timeout` 等异常场景都能在前端清晰看见补偿逻辑。
- share_text 可直接用于演示或聊天转发，不需要人工再润色太多。

## Task 6: 建立比赛终版验证体系
**目标：** 从“有几个单元测试”升级到“关键链路可回归、可验证、可演示”。

**文件：**
- 修改：`d:\美团AI\tests\test_conversation.py`
- 修改：`d:\美团AI\tests\test_parser.py`
- 修改：`d:\美团AI\tests\test_planner.py`
- 修改：`d:\美团AI\tests\test_executor.py`
- 新增：`d:\美团AI\tests\test_api.py`
- 新增：`d:\美团AI\tests\test_chat_stream.py`

**要做什么：**
- 补齐以下测试层次：
  - 对话状态机单元测试
  - parser/planner/executor 单元测试
  - API 级集成测试
  - SSE 流式接口测试
  - 对话 -> direct plan -> execute 的端到端主路径测试

**为什么：**
- 比赛终版最大的风险不是“功能少”，而是“现场某个分支突然挂掉”。测试要优先保住主链路。

**怎么做：**
1. 先为 `/chat`、`/chat/stream`、`/plan/direct` 写失败测试。
2. 再补 happy path：
   - 家庭场景全链路
   - 朋友场景全链路
3. 再补 fallback path：
   - LLM 不可用
   - SSE 解析异常
   - direct plan 失败降级
4. 清理 `tests/__pycache__` 并确保 `.gitignore` 忽略 pyc。

**验证：**
- `pytest` 可以稳定覆盖关键链路。
- 测试名称与行为一一对应，便于赛前快速回归。

## Task 7: 完成比赛终版文档与演示说明
**目标：** 让项目不仅代码能跑，而且任何人按文档都能在本地启动并理解亮点。

**文件：**
- 修改：`d:\美团AI\README.md`
- 修改：`d:\美团AI\design.md`
- 可选追加：`d:\美团AI\升级修改说明.md`

**要做什么：**
- 重写 README 为“比赛终版启动文档”。
- 重写 design.md 为“评审可读的产品/技术方案说明”。
- 将“用户视角、平台视角、评审视角”显式写入文档。

**为什么：**
- 比赛项目最终提交不是只有代码，评审看到的是“代码 + 演示 + 文档 + 说明”的总和。

**怎么做：**
1. README 明确：
   - 前后端启动
   - LLM/高德环境变量
   - 有 Key 与无 Key 的运行差异
   - 默认演示案例
   - 常见故障与 fallback
2. design.md 明确：
   - 对话架构
   - Goal 契约
   - planner 评分思路
   - 执行补偿机制
   - 为什么双场景保留仍能说服评委
3. 可选在“升级修改说明”中单列本轮升级点，便于导师/队友快速理解。

**验证：**
- 新同学拿到仓库后，仅按 README 即可启动。
- design.md 可直接用于答辩讲述主线。

## Delivery Sequence
### 阶段 A：先把主链路收敛
1. Task 1：统一 Goal 契约和 direct plan 主路径
2. Task 2：统一 LLM/规则双轨行为

### 阶段 B：再把结果质量做实
3. Task 3：用 Goal 反向增强 planner
4. Task 5：提升执行可信度和分享表达

### 阶段 C：最后做体验与验证封口
5. Task 4：重构前端聊天主路径和流式体验
6. Task 6：补齐测试和回归体系
7. Task 7：更新比赛终版文档与演示说明

## 风险与应对
- 风险 1：LLM 输出结构不稳定
  - 应对：始终保留 `ConversationOrchestrator` 规则兜底；`goal` 校验不通过即降级。
- 风险 2：前端流式链路复杂度上升
  - 应对：用 `test_chat_stream.py` 固化事件格式；前端对 `token/done/error` 三类事件分别处理。
- 风险 3：双场景同时保留导致规则膨胀
  - 应对：统一 Goal 契约，尽量把差异收敛在 planner 评分和 share 表达层，而不是 everywhere if/else。
- 风险 4：比赛前改动过大影响稳定性
  - 应对：每个 Task 完成后都保留可运行版本，严格按主链路做回归。

## Verification Steps
- 对话层验证
  - 家庭场景：从自然对话到 `ready_to_plan=true`，返回完整 `goal`。
  - 朋友场景：从自然对话到 `ready_to_plan=true`，返回完整 `goal`。
  - 改口、冲突、无效输入、小闲聊都有独立回归。
- 规划层验证
  - `/plan/direct` 成为前端默认主路径。
  - 同城同时间下，家庭/朋友主方案明显不同。
  - 主备方案、评分拆解、推荐理由完整可展示。
- 执行层验证
  - `normal`、`partial_failure`、`reserve_timeout` 至少三类场景可稳定演示。
  - 执行失败不静默，必须展示补偿动作。
- 前端验证
  - SSE 流式对话稳定显示。
  - 聊天阶段单列自然、ready 后生成方案过渡自然。
  - 地图缺失或接口异常时仍可完成文本级展示。
- 文档验证
  - README 可独立指导启动。
  - design.md 可支持答辩讲解。

## 任务级执行清单
### Task 1 清单
1. 为 `goal` 契约补失败测试
2. 统一 `api.py` chat / stream 输出结构
3. 统一 `conversation.py` ready 与 goal 关系
4. 统一 `llm_conversation.py` goal 归一化与校验
5. 前端改成 direct plan 默认主路径
6. 跑 conversation + api 回归

### Task 2 清单
1. 梳理对话行为清单
2. 收敛 LLM prompt
3. 补规则兜底重复回复控制
4. 补连续无效输入/冲突/改口测试
5. 验证 LLM 失败时体验不崩

### Task 3 清单
1. 先补 parser/planner 失败测试
2. 对齐 Goal 字段语义
3. 增强 scene-specific 评分
4. 增强 special_needs 可消费能力
5. 验证双场景明显差异

### Task 4 清单
1. 收敛 `App.tsx` 中聊天数据流
2. 完善 SSE token / done / error 处理
3. 清理 ready 前后的割裂展示
4. 收敛富文本渲染能力边界
5. 做流式和错误态回归

### Task 5 清单
1. 规范执行阶段字段
2. 强化失败补偿文案
3. 更新前端执行状态展示
4. 优化 share 输出
5. 做异常场景演示回归

### Task 6 清单
1. 新增 `test_api.py`
2. 新增 `test_chat_stream.py`
3. 补端到端 happy path
4. 补 fallback path
5. 清理 pycache / 忽略项

### Task 7 清单
1. 重写 README
2. 重写 design.md
3. 补默认案例与故障说明
4. 形成比赛演示顺序

