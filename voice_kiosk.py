import asyncio
import logging
from typing import Dict, List, Any
import speech_recognition as sr
import pyttsx3

logger = logging.getLogger(__name__)

class VoiceKiosk:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        
        # Configure TTS
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.8)
        
        # Calibrate microphone for ambient noise
        logger.info("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
        logger.info("Microphone calibrated")
        
    async def listen_for_wake_word(self) -> bool:
        """Listen for wake word (simplified version)"""
        try:
            with self.microphone as source:
                logger.info("Listening for wake word...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                
            # Simple wake word detection - you can replace with more sophisticated logic
            wake_word = self.recognizer.recognize_google(audio).lower()
            if "hello" in wake_word or "hey" in wake_word or "assistant" in wake_word:
                logger.info(f"Wake word detected: {wake_word}")
                return True
                
        except sr.WaitTimeoutError:
            pass  # No speech detected
        except sr.UnknownValueError:
            pass  # Speech not understood
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            
        return False
        
    async def record_audio(self, duration: int = 10) -> str:
        """Record audio and convert to text"""
        try:
            logger.info(f"Recording audio for {duration} seconds...")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=duration)
                
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Recorded text: {text}")
            return text
            
        except sr.UnknownValueError:
            return "*Could not understand audio*"
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return "*Speech recognition error*"
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return "*Recording failed*"
            
    def speak(self, text: str):
        """Convert text to speech"""
        try:
            logger.info(f"Speaking: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
    async def process_voice_interaction(self):
        """Complete voice interaction cycle"""
        # Listen for wake word
        if await self.listen_for_wake_word():
            # Record user speech
            user_text = await self.record_audio()
            return user_text
        return None

