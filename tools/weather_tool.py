"""
Weather Tool
Gets weather information (simplified version - can be extended with real API)
"""
import logging
import random

logger = logging.getLogger(__name__)

TOOL_NAME = "get_weather"
TOOL_PARAMS = "city"
TOOL_DESCRIPTION = "return the weather for a certain city"

# Mock weather data (replace with real API integration)
WEATHER_CONDITIONS = ["sunny", "cloudy", "partly cloudy", "rainy", "overcast"]
TEMPERATURES = range(50, 85)

async def execute(parameter):
    """Get weather for a city

    Args:
        parameter: City name

    Returns:
        String with weather information
    """
    logger.info(f"Executing weather tool for city: {parameter}")

    try:
        city = parameter if parameter else "unknown location"

        # Mock weather data
        condition = random.choice(WEATHER_CONDITIONS)
        temp = random.choice(TEMPERATURES)

        result = f"Here is the weather data: The weather in {city} is {condition} with a temperature of {temp}°F"
        logger.info(f"Weather tool result for {city}: {condition}, {temp}°F")

        return result

    except Exception as e:
        logger.error(f"Error in weather tool: {e}", exc_info=True)
        return f"Error getting weather: {e}"

# Tool definition dict
tool_def = {
    "name": TOOL_NAME,
    "params": TOOL_PARAMS,
    "description": TOOL_DESCRIPTION,
    "execution": execute
}
