from __future__ import annotations

from .executor import Executor
from .mock_tools import MockToolbox
from typing import Any

from .models import AgentOutput, PlanningOutput
from .parser import GoalParser
from .planner import Planner
from .share import ShareComposer


class LocalActivityAgent:
    def __init__(self) -> None:
        self.toolbox = MockToolbox()
        self.parser = GoalParser()
        self.planner = Planner(self.toolbox)
        self.executor = Executor(self.toolbox)
        self.share = ShareComposer()

    def plan(self, text: str, context: dict[str, Any] | None = None) -> PlanningOutput:
        goal = self.parser.parse(text, context)
        return self.planner.build_plan(goal)

    def execute(self, planning: PlanningOutput) -> AgentOutput:
        results = self.executor.run(planning.actions)
        summary = [
            f"{item.action_type}:{item.target}:{item.status}"
            for item in results
        ]
        share_text = self.share.compose(planning.goal, planning.itinerary, summary)
        return AgentOutput(
            planning=planning,
            execution_results=results,
            share_text=share_text,
            summary=summary,
        )
