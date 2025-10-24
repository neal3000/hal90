#!/usr/bin/env python3
"""
Test the improved movie selection logic
"""
import sys
import logging
from ollama import Client

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_movie_selection():
    """Test explicit movie selection from a list"""

    ollama_client = Client(host="http://localhost:11434")
    model = "qwen2.5:7b"

    # Test cases
    test_cases = [
        {
            "user_query": "play movie about a barbarian",
            "movies": ["Superman.mp4", "Airplane.mp4", "Red Sonja.mp4"],
            "expected": "Red Sonja.mp4"
        },
        {
            "user_query": "play a comedy",
            "movies": ["Superman.mp4", "Airplane.mp4", "Red Sonja.mp4"],
            "expected": "Airplane.mp4"
        },
        {
            "user_query": "play movie about kryptonian",
            "movies": ["Superman.mp4", "Airplane.mp4", "Red Sonja.mp4"],
            "expected": "Superman.mp4"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        logger.info("="*80)
        logger.info(f"TEST {i}: {test['user_query']}")
        logger.info("="*80)

        selection_prompt = f"""The user requested: "{test['user_query']}"

Available movies:
{chr(10).join(f'{j+1}. {movie}' for j, movie in enumerate(test['movies']))}

Which movie best matches the user's request? Consider the movie titles and what they might be about.
Respond with ONLY the filename (e.g., "Superman.mp4"), nothing else."""

        logger.info("\n📝 PROMPT:")
        logger.info("-"*80)
        logger.info(selection_prompt)
        logger.info("-"*80)

        try:
            response = ollama_client.chat(
                model=model,
                messages=[{"role": "user", "content": selection_prompt}]
            )

            selected = response['message']['content'].strip()
            logger.info(f"\n🎬 LLM SELECTED: {selected}")
            logger.info(f"   Expected: {test['expected']}")

            # Clean up response (might have quotes or extra text)
            if test['expected'].lower() in selected.lower():
                logger.info("   ✅ PASS")
            else:
                logger.info("   ❌ FAIL")

        except Exception as e:
            logger.error(f"❌ Error: {e}")

        logger.info("")

if __name__ == "__main__":
    test_movie_selection()
