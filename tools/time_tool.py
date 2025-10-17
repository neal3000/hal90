"""
Time Tool
Returns current date and time
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TOOL_NAME = "timenow"
TOOL_PARAMS = None
TOOL_DESCRIPTION = "return the current date and time"

async def execute(parameter=None):
    """Get current date and time

    Args:
        parameter: Not used

    Returns:
        String with current date and time
    """
    logger.info("Executing time tool")

    try:
        now = datetime.now()
        formatted_time = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")

        result = f"Here is the Date and current time: {formatted_time}"
        logger.info(f"Time tool result: {formatted_time}")

        return result

    except Exception as e:
        logger.error(f"Error in time tool: {e}", exc_info=True)
        return f"Error getting time: {e}"

# Tool definition dict
tool_def = {
    "name": TOOL_NAME,
    "params": TOOL_PARAMS,
    "description": TOOL_DESCRIPTION,
    "execution": execute
}
