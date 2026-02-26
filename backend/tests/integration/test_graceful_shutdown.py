"""Integration tests for graceful shutdown functionality."""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.shutdown import GracefulShutdown, setup_graceful_shutdown


class TestGracefulShutdown:
    """Test graceful shutdown handler."""

    def test_initialization(self):
        """Test shutdown handler initialization."""
        handler = GracefulShutdown(
            shutdown_timeout=10.0,
            force_shutdown_timeout=20.0,
        )
        
        assert handler.shutdown_timeout == 10.0
        assert handler.force_shutdown_timeout == 20.0
        assert handler.is_shutting_down is False
        assert handler.in_flight_requests == 0
        assert len(handler.shutdown_callbacks) == 0

    def test_register_shutdown_callback(self):
        """Test registering shutdown callbacks."""
        handler = GracefulShutdown()
        
        async def callback1():
            pass
        
        def callback2():
            pass
        
        handler.register_shutdown_callback(callback1)
        handler.register_shutdown_callback(callback2)
        
        assert len(handler.shutdown_callbacks) == 2
        assert callback1 in handler.shutdown_callbacks
        assert callback2 in handler.shutdown_callbacks

    def test_increment_decrement_requests(self):
        """Test request counter management."""
        handler = GracefulShutdown()
        
        assert handler.in_flight_requests == 0
        
        handler.increment_requests()
        assert handler.in_flight_requests == 1
        
        handler.increment_requests()
        assert handler.in_flight_requests == 2
        
        handler.decrement_requests()
        assert handler.in_flight_requests == 1
        
        handler.decrement_requests()
        assert handler.in_flight_requests == 0
        
        # Should not go below 0
        handler.decrement_requests()
        assert handler.in_flight_requests == 0

    @pytest.mark.asyncio
    async def test_wait_for_requests_no_requests(self):
        """Test waiting for requests when there are none."""
        handler = GracefulShutdown(shutdown_timeout=1.0)
        
        # Should return immediately
        await handler._wait_for_requests()
        
        assert handler.in_flight_requests == 0

    @pytest.mark.asyncio
    async def test_wait_for_requests_with_timeout(self):
        """Test waiting for requests with timeout."""
        handler = GracefulShutdown(shutdown_timeout=0.5)
        handler.in_flight_requests = 5
        
        # Should timeout after 0.5 seconds
        start = asyncio.get_event_loop().time()
        await handler._wait_for_requests()
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed >= 0.5
        assert handler.in_flight_requests == 5  # Still pending

    @pytest.mark.asyncio
    async def test_wait_for_requests_completes(self):
        """Test waiting for requests that complete."""
        handler = GracefulShutdown(shutdown_timeout=2.0)
        handler.in_flight_requests = 2
        
        async def decrement_after_delay():
            await asyncio.sleep(0.2)
            handler.decrement_requests()
            await asyncio.sleep(0.2)
            handler.decrement_requests()
        
        # Start decrementing in background
        asyncio.create_task(decrement_after_delay())
        
        # Should complete before timeout
        start = asyncio.get_event_loop().time()
        await handler._wait_for_requests()
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed < 1.0
        assert handler.in_flight_requests == 0

    @pytest.mark.asyncio
    async def test_execute_shutdown_callbacks_success(self):
        """Test executing shutdown callbacks successfully."""
        handler = GracefulShutdown()
        
        callback1_called = False
        callback2_called = False
        
        async def async_callback():
            nonlocal callback1_called
            callback1_called = True
        
        def sync_callback():
            nonlocal callback2_called
            callback2_called = True
        
        handler.register_shutdown_callback(async_callback)
        handler.register_shutdown_callback(sync_callback)
        
        await handler._execute_shutdown_callbacks()
        
        assert callback1_called
        assert callback2_called

    @pytest.mark.asyncio
    async def test_execute_shutdown_callbacks_with_error(self):
        """Test executing shutdown callbacks with errors."""
        handler = GracefulShutdown()
        
        callback2_called = False
        
        async def failing_callback():
            raise ValueError("Test error")
        
        async def success_callback():
            nonlocal callback2_called
            callback2_called = True
        
        handler.register_shutdown_callback(failing_callback)
        handler.register_shutdown_callback(success_callback)
        
        # Should not raise, should continue with other callbacks
        await handler._execute_shutdown_callbacks()
        
        assert callback2_called

    @pytest.mark.asyncio
    async def test_execute_shutdown_callbacks_timeout(self):
        """Test executing shutdown callbacks with timeout."""
        handler = GracefulShutdown(shutdown_timeout=0.5)
        
        async def slow_callback():
            await asyncio.sleep(10)  # Will timeout
        
        handler.register_shutdown_callback(slow_callback)
        
        # Should timeout but not raise
        start = asyncio.get_event_loop().time()
        await handler._execute_shutdown_callbacks()
        elapsed = asyncio.get_event_loop().time() - start
        
        assert elapsed < 1.0  # Should timeout quickly

    @pytest.mark.asyncio
    async def test_handle_shutdown_signal(self):
        """Test handling shutdown signal."""
        handler = GracefulShutdown(shutdown_timeout=0.5)
        
        callback_called = False
        
        async def callback():
            nonlocal callback_called
            callback_called = True
        
        handler.register_shutdown_callback(callback)
        
        # Simulate shutdown signal
        await handler._handle_shutdown(signal.SIGTERM)
        
        assert handler.is_shutting_down
        assert callback_called
        assert handler.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_handle_shutdown_already_in_progress(self):
        """Test handling shutdown when already in progress."""
        handler = GracefulShutdown()
        handler.is_shutting_down = True
        
        callback_called = False
        
        async def callback():
            nonlocal callback_called
            callback_called = True
        
        handler.register_shutdown_callback(callback)
        
        # Should return early
        await handler._handle_shutdown(signal.SIGTERM)
        
        assert not callback_called

    def test_setup_graceful_shutdown(self):
        """Test setup function."""
        handler = setup_graceful_shutdown(
            shutdown_timeout=15.0,
            force_shutdown_timeout=30.0,
        )
        
        assert isinstance(handler, GracefulShutdown)
        assert handler.shutdown_timeout == 15.0
        assert handler.force_shutdown_timeout == 30.0


class TestWorkerGracefulShutdown:
    """Test Taskiq worker graceful shutdown."""

    def test_worker_signal_handler_registration(self):
        """Test that worker registers signal handlers."""
        from app.workers.broker import startup_event
        
        # Mock state
        mock_state = MagicMock()
        mock_state.worker_id = "test-worker-1"
        
        # Should not raise
        asyncio.run(startup_event(mock_state))

    def test_worker_is_shutting_down(self):
        """Test worker shutdown state tracking."""
        from app.workers.broker import is_shutting_down, _handle_shutdown_signal
        
        # Initially not shutting down
        assert not is_shutting_down()
        
        # Simulate shutdown signal
        _handle_shutdown_signal(signal.SIGTERM)
        
        # Should be shutting down
        assert is_shutting_down()

    @pytest.mark.asyncio
    async def test_worker_shutdown_event(self):
        """Test worker shutdown event handler."""
        from app.workers.broker import shutdown_event
        
        mock_state = MagicMock()
        mock_state.worker_id = "test-worker-1"
        
        # Should complete without error
        await shutdown_event(mock_state)


@pytest.mark.integration
class TestEndToEndGracefulShutdown:
    """End-to-end tests for graceful shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_with_in_flight_requests(self):
        """Test shutdown waits for in-flight requests."""
        handler = GracefulShutdown(shutdown_timeout=2.0)
        
        # Simulate in-flight requests
        handler.increment_requests()
        handler.increment_requests()
        
        request_completed = False
        
        async def complete_request():
            nonlocal request_completed
            await asyncio.sleep(0.5)
            handler.decrement_requests()
            handler.decrement_requests()
            request_completed = True
        
        # Start completing requests
        asyncio.create_task(complete_request())
        
        # Trigger shutdown
        await handler._handle_shutdown(signal.SIGTERM)
        
        # Requests should have completed
        assert request_completed
        assert handler.in_flight_requests == 0
        assert handler.shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_with_callbacks(self):
        """Test shutdown executes all callbacks."""
        handler = GracefulShutdown(shutdown_timeout=2.0)
        
        callback_order = []
        
        async def callback1():
            callback_order.append(1)
        
        async def callback2():
            callback_order.append(2)
        
        async def callback3():
            callback_order.append(3)
        
        handler.register_shutdown_callback(callback1)
        handler.register_shutdown_callback(callback2)
        handler.register_shutdown_callback(callback3)
        
        # Trigger shutdown
        await handler._handle_shutdown(signal.SIGTERM)
        
        # All callbacks should have been called in order
        assert callback_order == [1, 2, 3]
        assert handler.shutdown_event.is_set()

