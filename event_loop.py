"""
Event Loop Coordinator
Manages the main async event loop and coordinates subsystems
"""
import asyncio
import logging
from typing import Callable, Dict, Any, Optional
from enum import IntEnum
import time

logger = logging.getLogger(__name__)

class AppStatus(IntEnum):
    """Application states matching frontend expectations"""
    BOOT = 3
    IDLE = 1
    RECORDING = 0
    PROCESSING_RECORDING = 4
    THINKING = 2
    SPEAKING = 5
    SCREENSAVER = 6

class EventLoopCoordinator:
    """Coordinates async operations and state transitions"""

    def __init__(self, config):
        """Initialize event loop coordinator

        Args:
            config: Configuration object with system settings
        """
        logger.info("Initializing EventLoopCoordinator")
        self.config = config
        self.loop = None
        self.running = False
        self.current_state = AppStatus.BOOT
        self.state_callbacks: Dict[AppStatus, list] = {}
        self.transition_lock = asyncio.Lock()
        self.background_tasks = set()
        self.last_activity_time = time.time()
        self.screensaver_task = None

        logger.info("EventLoopCoordinator initialized")

    def get_loop(self):
        """Get or create the asyncio event loop"""
        if self.loop is None:
            logger.info("Creating new asyncio event loop")
            try:
                self.loop = asyncio.get_event_loop()
                if self.loop.is_closed():
                    logger.warning("Event loop was closed, creating new one")
                    self.loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.loop)
            except RuntimeError:
                logger.info("No event loop found, creating new one")
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            logger.info(f"Event loop created: {self.loop}")
        return self.loop

    async def transition_state(self, new_state: AppStatus, metadata: Dict[str, Any] = None):
        """Transition to a new application state

        Args:
            new_state: Target state to transition to
            metadata: Optional data about the state transition
        """
        async with self.transition_lock:
            old_state = self.current_state
            logger.info(f"State transition: {old_state.name} -> {new_state.name}")

            if metadata:
                logger.info(f"Transition metadata: {metadata}")

            # Validate transition
            if not self._is_valid_transition(old_state, new_state):
                logger.warning(f"Invalid state transition: {old_state.name} -> {new_state.name}, allowing anyway")

            self.current_state = new_state
            self.last_activity_time = time.time()

            # Execute callbacks for this state
            await self._execute_state_callbacks(new_state, metadata)

            logger.info(f"State transition complete: now in {new_state.name}")

    def _is_valid_transition(self, from_state: AppStatus, to_state: AppStatus) -> bool:
        """Check if a state transition is valid

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is allowed
        """
        # Define valid transitions
        valid_transitions = {
            AppStatus.BOOT: [AppStatus.IDLE, AppStatus.THINKING, AppStatus.SPEAKING],
            AppStatus.IDLE: [AppStatus.RECORDING, AppStatus.SCREENSAVER, AppStatus.THINKING],
            AppStatus.RECORDING: [AppStatus.PROCESSING_RECORDING, AppStatus.IDLE],
            AppStatus.PROCESSING_RECORDING: [AppStatus.THINKING, AppStatus.IDLE],
            AppStatus.THINKING: [AppStatus.SPEAKING, AppStatus.IDLE],
            AppStatus.SPEAKING: [AppStatus.IDLE, AppStatus.RECORDING],
            AppStatus.SCREENSAVER: [AppStatus.IDLE, AppStatus.RECORDING],
        }

        allowed = to_state in valid_transitions.get(from_state, [])
        if not allowed:
            logger.debug(f"Transition {from_state.name} -> {to_state.name} not in predefined valid transitions")
        return allowed

    def register_state_callback(self, state: AppStatus, callback: Callable):
        """Register a callback to be called when entering a state

        Args:
            state: State to watch for
            callback: Async function to call when entering state
        """
        if state not in self.state_callbacks:
            self.state_callbacks[state] = []
        self.state_callbacks[state].append(callback)
        logger.info(f"Registered callback for state {state.name}: {callback.__name__}")

    async def _execute_state_callbacks(self, state: AppStatus, metadata: Dict[str, Any] = None):
        """Execute all callbacks for a given state

        Args:
            state: State that was entered
            metadata: Optional data to pass to callbacks
        """
        callbacks = self.state_callbacks.get(state, [])
        logger.info(f"Executing {len(callbacks)} callback(s) for state {state.name}")

        for callback in callbacks:
            try:
                logger.debug(f"Calling callback: {callback.__name__}")
                if asyncio.iscoroutinefunction(callback):
                    await callback(metadata)
                else:
                    callback(metadata)
                logger.debug(f"Callback {callback.__name__} completed successfully")
            except Exception as e:
                logger.error(f"Error in state callback {callback.__name__}: {e}", exc_info=True)

    def create_task(self, coro, name: str = None):
        """Create a background task and track it

        Args:
            coro: Coroutine to run as a task
            name: Optional name for debugging

        Returns:
            asyncio.Task object
        """
        task_name = name or str(coro)
        logger.info(f"Creating background task: {task_name}")

        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(lambda t: self._task_done_callback(t, task_name))

        return task

    def _task_done_callback(self, task, task_name: str):
        """Callback when a background task completes

        Args:
            task: Completed task
            task_name: Name of the task for logging
        """
        self.background_tasks.discard(task)

        try:
            exception = task.exception()
            if exception:
                logger.error(f"Background task '{task_name}' failed with exception: {exception}", exc_info=exception)
            else:
                logger.info(f"Background task '{task_name}' completed successfully")
        except asyncio.CancelledError:
            logger.info(f"Background task '{task_name}' was cancelled")
        except Exception as e:
            logger.error(f"Error checking task '{task_name}' result: {e}", exc_info=True)

    async def start_screensaver_monitor(self):
        """Monitor for inactivity and trigger screensaver"""
        logger.info("Starting screensaver monitor")

        while self.running:
            try:
                await asyncio.sleep(1)  # Check every second

                if self.current_state in [AppStatus.IDLE, AppStatus.SCREENSAVER]:
                    idle_time = time.time() - self.last_activity_time

                    if idle_time >= self.config.SCREENSAVER_TIMEOUT and self.current_state == AppStatus.IDLE:
                        logger.info(f"Idle timeout reached ({idle_time:.1f}s), activating screensaver")
                        await self.transition_state(AppStatus.SCREENSAVER)

            except asyncio.CancelledError:
                logger.info("Screensaver monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in screensaver monitor: {e}", exc_info=True)

    def reset_activity_timer(self):
        """Reset the inactivity timer"""
        self.last_activity_time = time.time()
        logger.debug(f"Activity timer reset at {self.last_activity_time}")

    async def shutdown(self):
        """Gracefully shutdown the event loop"""
        logger.info("Shutting down EventLoopCoordinator")
        self.running = False

        # Cancel all background tasks
        logger.info(f"Cancelling {len(self.background_tasks)} background task(s)")
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            logger.info("Waiting for background tasks to complete...")
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Cancel screensaver task
        if self.screensaver_task and not self.screensaver_task.done():
            logger.info("Cancelling screensaver task")
            self.screensaver_task.cancel()
            try:
                await self.screensaver_task
            except asyncio.CancelledError:
                pass

        logger.info("EventLoopCoordinator shutdown complete")

    async def run(self):
        """Main event loop run method"""
        logger.info("Starting EventLoopCoordinator main loop")
        self.running = True

        # Start screensaver monitor
        self.screensaver_task = self.create_task(
            self.start_screensaver_monitor(),
            name="screensaver_monitor"
        )

        logger.info("EventLoopCoordinator running")

        # Keep running until shutdown
        try:
            while self.running:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info("EventLoopCoordinator run loop cancelled")
        finally:
            await self.shutdown()

    def get_state(self) -> AppStatus:
        """Get current application state"""
        return self.current_state

    def get_state_name(self) -> str:
        """Get current state name as string"""
        return self.current_state.name

    def is_busy(self) -> bool:
        """Check if system is in a busy state"""
        busy_states = [AppStatus.RECORDING, AppStatus.PROCESSING_RECORDING,
                       AppStatus.THINKING, AppStatus.SPEAKING]
        is_busy = self.current_state in busy_states
        logger.debug(f"System busy check: {is_busy} (state: {self.current_state.name})")
        return is_busy
