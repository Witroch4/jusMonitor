"""Graceful shutdown handler for FastAPI application."""

import asyncio
import signal
import sys
from typing import Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class GracefulShutdown:
    """
    Handles graceful shutdown of the application.
    
    Responsibilities:
    - Capture SIGTERM and SIGINT signals
    - Stop accepting new requests
    - Wait for in-flight requests to complete
    - Shutdown Taskiq workers gracefully
    - Close database connections
    - Cleanup other resources
    """

    def __init__(
        self,
        shutdown_timeout: float = 30.0,
        force_shutdown_timeout: float = 60.0,
    ):
        """
        Initialize graceful shutdown handler.
        
        Args:
            shutdown_timeout: Time to wait for graceful shutdown (seconds)
            force_shutdown_timeout: Time before forcing shutdown (seconds)
        """
        self.shutdown_timeout = shutdown_timeout
        self.force_shutdown_timeout = force_shutdown_timeout
        self.is_shutting_down = False
        self.shutdown_event = asyncio.Event()
        self.in_flight_requests = 0
        self.shutdown_callbacks: list[Callable] = []
        
        logger.info(
            "graceful_shutdown_initialized",
            shutdown_timeout=shutdown_timeout,
            force_shutdown_timeout=force_shutdown_timeout,
        )

    def register_shutdown_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called during shutdown.
        
        Args:
            callback: Async function to call during shutdown
        """
        self.shutdown_callbacks.append(callback)
        logger.debug("shutdown_callback_registered", callback=callback.__name__)

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for SIGTERM and SIGINT."""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self._handle_shutdown(s)),
            )
        
        logger.info("signal_handlers_configured", signals=["SIGTERM", "SIGINT"])

    async def _handle_shutdown(self, sig: signal.Signals) -> None:
        """
        Handle shutdown signal.
        
        Args:
            sig: Signal that triggered shutdown
        """
        if self.is_shutting_down:
            logger.warning("shutdown_already_in_progress", signal=sig.name)
            return

        self.is_shutting_down = True
        logger.info("shutdown_initiated", signal=sig.name)

        try:
            # Wait for in-flight requests with timeout
            await self._wait_for_requests()

            # Execute shutdown callbacks
            await self._execute_shutdown_callbacks()

            # Signal that shutdown is complete
            self.shutdown_event.set()
            logger.info("shutdown_completed")

        except asyncio.TimeoutError:
            logger.error(
                "shutdown_timeout_exceeded",
                timeout=self.shutdown_timeout,
            )
            # Force shutdown
            self.shutdown_event.set()
        except Exception as e:
            logger.error(
                "shutdown_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            self.shutdown_event.set()
        finally:
            # CRITICAL: exit the process so Docker/supervisor can restart it.
            # Without this, the process stays alive permanently rejecting all
            # requests with 503 after a SIGTERM/SIGINT is received.
            logger.info("process_exit_after_shutdown")
            sys.exit(0)

    async def _wait_for_requests(self) -> None:
        """Wait for in-flight requests to complete."""
        if self.in_flight_requests == 0:
            logger.info("no_in_flight_requests")
            return

        logger.info(
            "waiting_for_requests",
            in_flight=self.in_flight_requests,
            timeout=self.shutdown_timeout,
        )

        start_time = asyncio.get_event_loop().time()
        
        while self.in_flight_requests > 0:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed >= self.shutdown_timeout:
                logger.warning(
                    "shutdown_timeout_requests_remaining",
                    remaining=self.in_flight_requests,
                )
                break

            await asyncio.sleep(0.1)

        logger.info(
            "requests_completed",
            remaining=self.in_flight_requests,
        )

    async def _execute_shutdown_callbacks(self) -> None:
        """Execute all registered shutdown callbacks."""
        logger.info(
            "executing_shutdown_callbacks",
            count=len(self.shutdown_callbacks),
        )

        for callback in self.shutdown_callbacks:
            try:
                logger.debug("executing_callback", callback=callback.__name__)
                
                if asyncio.iscoroutinefunction(callback):
                    await asyncio.wait_for(
                        callback(),
                        timeout=self.shutdown_timeout / len(self.shutdown_callbacks),
                    )
                else:
                    callback()
                
                logger.debug("callback_completed", callback=callback.__name__)
            except asyncio.TimeoutError:
                logger.error(
                    "callback_timeout",
                    callback=callback.__name__,
                )
            except Exception as e:
                logger.error(
                    "callback_error",
                    callback=callback.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                )

    def increment_requests(self) -> None:
        """Increment in-flight request counter."""
        self.in_flight_requests += 1

    def decrement_requests(self) -> None:
        """Decrement in-flight request counter."""
        self.in_flight_requests = max(0, self.in_flight_requests - 1)

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown to complete."""
        await self.shutdown_event.wait()


# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    """Get or create the global shutdown handler."""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdown()
    return _shutdown_handler


def setup_graceful_shutdown(
    shutdown_timeout: float = 30.0,
    force_shutdown_timeout: float = 60.0,
) -> GracefulShutdown:
    """
    Setup graceful shutdown for the application.
    
    Args:
        shutdown_timeout: Time to wait for graceful shutdown (seconds)
        force_shutdown_timeout: Time before forcing shutdown (seconds)
    
    Returns:
        GracefulShutdown instance
    """
    global _shutdown_handler
    _shutdown_handler = GracefulShutdown(
        shutdown_timeout=shutdown_timeout,
        force_shutdown_timeout=force_shutdown_timeout,
    )
    return _shutdown_handler
