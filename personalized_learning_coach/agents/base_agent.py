from typing import Dict, Any, Union, Awaitable
import abc
import logging
import asyncio
import inspect

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    """
    Base class for agents in the personalized_learning_coach project.

    Subclasses should implement `run` (synchronous) or `run_async` (asynchronous)
    depending on usage. The default `run_async` will call `run` in a thread
    pool so synchronous implementations remain compatible with async callers.

    Notes:
    - If a subclass implements `run` as an `async def` (i.e. returns a coroutine),
      this implementation will detect that and await the coroutine instead of
      running it inside an executor.
    """

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"

    @abc.abstractmethod
    def run(self, payload: Dict[str, Any]) -> Union[Dict[str, Any], Awaitable[Dict[str, Any]]]:
        """Run the agent synchronously or return an awaitable.
        Must be implemented by subclasses.

        Args:
            payload: Arbitrary dict containing input data for the agent.

        Returns:
            A dict containing the agent's result, or an awaitable that resolves
            to that dict.
        """
        raise NotImplementedError()

    async def run_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional asynchronous entrypoint. By default this will delegate to
        `run` using an executor so existing synchronous subclasses work when
        called from async code.

        Behavior:
         - If `run` returns an awaitable/coroutine, await it directly.
         - Otherwise, if an event loop is running, execute `run` in the default
           executor to avoid blocking the loop.
         - If no event loop is running, call `run` synchronously and return the result.
        """
        # Call run() directly — it might return a coroutine/awaitable
        try:
            result = self.run(payload)
        except asyncio.CancelledError:
            # Propagate cancellation
            raise
        except Exception:
            logger.exception("Synchronous run() raised an exception for %s", self)
            raise

        # If run returned an awaitable/coroutine, await it
        if inspect.isawaitable(result):
            try:
                return await result  # type: ignore[return-value]
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Awaiting result from run() failed for %s", self)
                raise

        # Otherwise, result is a regular value; if we're already in a running loop,
        # run the blocking call in the executor so we don't block the event loop.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: return the sync result directly
            return result  # type: ignore[return-value]

        # We're inside an event loop — run the sync call in an executor.
        logger.debug("Delegating to synchronous run() in executor for %s", self)
        try:
            return await loop.run_in_executor(None, lambda: result)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("run_in_executor failed for %s", self)
            raise