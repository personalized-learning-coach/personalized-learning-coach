"""
Tool registry for the personalized_learning_coach project.

Thread-safe registry with a synchronous entrypoint (execute_tool) and an async
entrypoint (execute_tool_async) so callers in either synchronous or asynchronous
contexts can execute registered tools safely.

See docstrings below for usage notes.
"""
from __future__ import annotations

import asyncio
import inspect
import threading
from typing import Any, Callable, Dict, List, Optional


class ToolRegistry:
    """Thread-safe registry for tools.

    See module docstring for conventions and usage.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def register_tool(self, tool_instance: Any) -> None:
        """Register a tool instance or callable.

        Raises ValueError for missing name or duplicate registration.
        """
        with self._lock:
            # Determine name
            name = None
            if hasattr(tool_instance, "name") and isinstance(getattr(tool_instance, "name"), str):
                name = getattr(tool_instance, "name")
            elif callable(tool_instance) and hasattr(tool_instance, "__name__"):
                name = getattr(tool_instance, "__name__")

            if not name:
                raise ValueError("Tool must have a 'name' attribute or be a named callable")

            if name in self._tools:
                raise ValueError(f"Tool with name '{name}' is already registered")

            # Keep whatever the tool provides for input_schema/description
            input_schema = getattr(tool_instance, "input_schema", None)
            description = getattr(tool_instance, "description", "")

            self._tools[name] = {
                "impl": tool_instance,
                "input_schema": input_schema,
                "description": description,
            }

    def get_tool(self, name: str) -> Optional[Any]:
        """Return the registered tool metadata, or None if not found."""
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return a list of tool definitions suitable for exposing to an LLM."""
        with self._lock:
            result: List[Dict[str, Any]] = []
            for name, entry in self._tools.items():
                result.append({
                    "name": name,
                    "description": entry.get("description", ""),
                    "input_schema": entry.get("input_schema") or {},
                })
            return result

    def _validate_payload(self, schema: Optional[Dict[str, Any]], payload: Dict[str, Any]) -> None:
        """Minimal validation: supports schema['required'] as a list of required keys."""
        if not schema or not isinstance(schema, dict):
            return

        required = schema.get("required")
        if required and isinstance(required, (list, tuple)):
            missing = [k for k in required if k not in payload]
            if missing:
                raise ValueError(f"Payload is missing required keys: {missing}")

    def _resolve_target(self, impl: Any) -> Optional[Callable[..., Any]]:
        """Return a callable to invoke (either impl.run or impl itself)."""
        if hasattr(impl, "run") and callable(getattr(impl, "run")):
            return getattr(impl, "run")
        if callable(impl):
            return impl
        return None

    def execute_tool(self, name: str, payload: Dict[str, Any]) -> Any:
        """Synchronous execution entrypoint.

        If the tool is asynchronous and there's no running event loop, this will
        use asyncio.run(...) to execute it. If there is an active event loop
        and the tool is async, a RuntimeError is raised instructing callers to
        use `await execute_tool_async(...)`.
        """
        with self._lock:
            entry = self._tools.get(name)

        if not entry:
            raise ValueError(f"Tool '{name}' not found")

        impl = entry["impl"]
        schema = entry.get("input_schema")

        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dict")

        self._validate_payload(schema, payload)

        target = self._resolve_target(impl)
        if not target:
            raise ValueError(f"Tool '{name}' is not executable (no 'run' method and not callable)")

        # If target is a coroutine function, handle with asyncio.run when safe.
        if inspect.iscoroutinefunction(target):
            # Check for running loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                raise RuntimeError(
                    "Attempted to synchronously execute an async tool from inside an active event loop. "
                    "Please call await default_registry().execute_tool_async(name, payload) instead."
                )
            # Safe to run the coroutine synchronously
            return asyncio.run(target(payload))

        # Synchronous callable: just call it and return result
        return target(payload)

    async def execute_tool_async(self, name: str, payload: Dict[str, Any]) -> Any:
        """Asynchronous execution entrypoint.

        This method is safe to call from inside an active asyncio event loop.
        - If the tool is async, it is awaited.
        - If the tool is sync, it is run in the default threadpool executor.
        """
        # Do the registry lookup under lock to avoid race conditions
        with self._lock:
            entry = self._tools.get(name)

        if not entry:
            raise ValueError(f"Tool '{name}' not found")

        impl = entry["impl"]
        schema = entry.get("input_schema")

        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dict")

        self._validate_payload(schema, payload)

        target = self._resolve_target(impl)
        if not target:
            raise ValueError(f"Tool '{name}' is not executable (no 'run' method and not callable)")

        # Call target; if it returns a coroutine, await it; if not, wrap sync I/O into executor
        try:
            maybe = target(payload)
        except Exception:
            # If calling the sync function raises immediately, propagate
            raise

        if asyncio.iscoroutine(maybe):
            return await maybe

        # Not a coroutine — it is synchronous. Run in executor to avoid blocking loop.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: maybe)

# Module-level default registry
_default_registry: Optional[ToolRegistry] = None


def default_registry() -> ToolRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry