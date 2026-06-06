# Trae AI 技能包

将 Hermes Agent 的开发技能转化为 Trae 国际版可用的规则文件。

## 文件结构

```
trae-skills/
├── .trae/rules/            # Trae 项目级规则（复制到项目根目录使用）
│   ├── tdd-workflow.md           # TDD 红绿重构流程
│   ├── systematic-debugging.md   # 系统化调试 4 步法
│   ├── pre-commit-verification.md # 预提交安全检查
│   ├── pr-workflow.md            # GitHub PR 工作流
│   ├── code-review-checklist.md  # 代码审查清单
│   └── writing-implementation-plans.md  # 实现计划写法
├── CLAUDE.md                # 主规则文件（复制到项目根目录）
└── README.md
```

## 使用方式

### 方式一：复制到项目根目录
```bash
# 复制 .trae/rules/ 到项目
cp -r .trae/rules /path/to/your/project/.trae/

# 复制 CLAUDE.md 到项目根目录
cp CLAUDE.md /path/to/your/project/
```

### 方式二：选择性使用
Trae 会自动读取项目根目录的 `.trae/rules/` 和 `CLAUDE.md`。
只复制你需要的规则文件即可。

## 技能来源

| 规则文件 | 来源 Hermes Skill |
|---------|------------------|
| tdd-workflow | software-development/test-driven-development |
| systematic-debugging | software-development/systematic-debugging |
| pre-commit-verification | software-development/requesting-code-review |
| pr-workflow | github/github-pr-workflow |
| code-review-checklist | github/github-code-review + gstack-review |
| writing-implementation-plans | software-development/writing-plans |
| CLAUDE.md | 综合所有 skill 的精要 |

## 说明

这些规则已将 Hermes Agent 专属的命令（如 delegate_task、skill_view 等）替换为通用的 Trae 可用格式。
CLAUDE.md 是 Trae 原生支持的主上下文文件，.trae/rules/ 下的规则文件会被 Trae 自动加载。
