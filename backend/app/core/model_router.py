from dataclasses import dataclass


@dataclass
class RouteDecision:
    model: str
    reason: str


class ModelRouter:
    """
    Lightweight routing policy.
    Replace with real provider latency/cost metrics later.
    """

    def pick(self, task_type: str, latency_priority: bool = True) -> RouteDecision:
        if latency_priority and task_type in {"chat", "quick_review"}:
            return RouteDecision(model="fast-model", reason="low-latency path")
        if task_type in {"deep_review", "test_generation"}:
            return RouteDecision(model="strong-model", reason="quality path")
        return RouteDecision(model="balanced-model", reason="default path")


router = ModelRouter()
