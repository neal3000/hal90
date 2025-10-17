"""
Finished Tool
Signals that the agent has completed its task
"""
import logging

logger = logging.getLogger(__name__)

TOOL_NAME = "finished"
TOOL_PARAMS = None
TOOL_DESCRIPTION = "call this when you have completed the user's request"

async def execute(parameter=None):
    """Signal task completion

    Args:
        parameter: Optional completion message

    Returns:
        Completion acknowledgment
    """
    logger.info("Executing finished tool - task complete")

    try:
        if parameter:
            result = f"Task completed: {parameter}"
        else:
            result = "Task completed successfully"

        logger.info("Finished tool executed - agent task complete")
        return result

    except Exception as e:
        logger.error(f"Error in finished tool: {e}", exc_info=True)
        return "Task completion signaled"

# Tool definition dict
tool_def = {
    "name": TOOL_NAME,
    "params": TOOL_PARAMS,
    "description": TOOL_DESCRIPTION,
    "execution": execute
}
