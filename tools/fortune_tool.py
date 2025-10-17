"""
Fortune Tool
Returns random fortune/quote
"""
import logging
import random

logger = logging.getLogger(__name__)

TOOL_NAME = "get_fortune"
TOOL_PARAMS = None
TOOL_DESCRIPTION = "get a random fortune or quote"

# Fortune database
FORTUNES = [
    "A journey of a thousand miles begins with a single step.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "Your future depends on many things, but mostly on you.",
    "The fortune you seek is in another cookie.",
    "A smooth sea never made a skilled sailor.",
    "Every exit is an entry somewhere else.",
    "Life is what happens while you're busy making other plans.",
    "The only way to do great work is to love what you do.",
    "Innovation distinguishes between a leader and a follower.",
    "Stay hungry, stay foolish.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "Believe you can and you're halfway there.",
    "The only impossible journey is the one you never begin.",
    "Today is your opportunity to build the tomorrow you want.",
]

async def execute(parameter=None):
    """Get a random fortune

    Args:
        parameter: Not used

    Returns:
        Random fortune string
    """
    logger.info("Executing fortune tool")

    try:
        fortune = random.choice(FORTUNES)
        result = f"Fortune: '{fortune}'"

        logger.info(f"Fortune tool result: {fortune}")
        return result

    except Exception as e:
        logger.error(f"Error in fortune tool: {e}", exc_info=True)
        return f"Error getting fortune: {e}"

# Tool definition dict
tool_def = {
    "name": TOOL_NAME,
    "params": TOOL_PARAMS,
    "description": TOOL_DESCRIPTION,
    "execution": execute
}
