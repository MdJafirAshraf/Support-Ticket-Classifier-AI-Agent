import time
from typing import Any, Callable
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentMiddleware, AgentState, ToolCallRequest


def _truncate(value: Any, limit: int = 400) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + f"... [{len(text)-limit} more chars]"


class LoggingMiddleware(AgentMiddleware):
    """
    Observability middleware. Logs agent name, model result, tool name,
    tool args, and tool result — truncated so logs stay readable.
    """

    def __init__(self, agent_name: str = "agent", max_log_chars: int = 400):
        super().__init__()
        self.agent_name = agent_name
        self.max_log_chars = max_log_chars

    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self._log("AGENT START", {"agent": self.agent_name})
        return {"_agent_start_time": time.perf_counter()}

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        model_response = []
        for message in state.get("messages", []):
            print("\n---")
            print(message.content)
            model_response.append(message.content)

        self._log("MODEL START", {
            "agent": self.agent_name,
            "message_count": len(state.get("messages", [])),
            "current message": model_response[-1]
        })
        return {"_model_start_time": time.perf_counter()}

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        start_time = state.get("_model_start_time")
        duration = time.perf_counter() - start_time if start_time else None

        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        content = getattr(last, "content", "") if last else ""
        tool_calls = getattr(last, "tool_calls", None) if last else None

        if content:
            result_repr = content
        elif tool_calls:
            result_repr = f"[tool_call] {tool_calls}"
        else:
            result_repr = "[empty response]"

        self._log("MODEL END", {
            "agent": self.agent_name,
            "duration": self._format_duration(duration),
            "result": _truncate(result_repr, self.max_log_chars),
        })
        return None

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]):
        tool_name = request.tool_call.get("name", "unknown")
        arguments = request.tool_call.get("args", {})

        log_data = {"agent": self.agent_name, "tool": tool_name, "arguments": arguments}
        if tool_name == "task" and "subagent_type" in arguments:
            log_data["subagent"] = arguments["subagent_type"]

        self._log("TOOL START", log_data)

        start_time = time.perf_counter()
        try:
            result = handler(request)
            duration = time.perf_counter() - start_time

            self._log("TOOL END", {
                "agent": self.agent_name,
                "tool": tool_name,
                "status": "SUCCESS",
                "duration": self._format_duration(duration),
                "result": _truncate(result, self.max_log_chars),
            })
            return result

        except Exception as exc:
            duration = time.perf_counter() - start_time
            self._log("TOOL END", {
                "agent": self.agent_name,
                "tool": tool_name,
                "status": "FAILED",
                "duration": self._format_duration(duration),
                "error": str(exc),
            })
            raise

    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        start_time = state.get("_agent_start_time")
        duration = time.perf_counter() - start_time if start_time else None

        log_data = {
            "agent": self.agent_name,
            "status": "SUCCESS",
            "duration": self._format_duration(duration),
        }

        # Surfaces whether response_format actually produced data — would
        # have caught the empty-coder-response bug immediately.
        structured = state.get("structured_response")
        if structured is not None:
            log_data["structured_response"] = _truncate(structured, self.max_log_chars)

        self._log("AGENT END", log_data)
        return None

    def _log(self, event: str, data: dict[str, Any]) -> None:
        print()
        print("=" * 60)
        print(f"[{event}]")
        for key, value in data.items():
            print(f"{key}: {value}")
        print("=" * 60)

    @staticmethod
    def _format_duration(duration: float | None) -> str:
        return "unknown" if duration is None else f"{duration:.3f}s"


class IterationGuardMiddleware(AgentMiddleware):
    """Caps main-agent model calls to stop runaway delegation loops."""

    def __init__(self, max_iterations: int = 6):
        super().__init__()
        self.max_iterations = max_iterations

    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        count = state.get("_iteration_count", 0) + 1
        if count > self.max_iterations:
            raise RuntimeError(
                f"Iteration guard tripped: exceeded {self.max_iterations} model calls."
            )
        return {"_iteration_count": count}