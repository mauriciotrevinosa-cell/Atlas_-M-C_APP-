"""
ARIA Voice Terminal

Voice mode para terminal con Speech-to-Text y Text-to-Speech
Soporta push-to-talk y modo continuo

Features:
- Speech recognition (Google/Whisper)
- Text-to-speech (gTTS/ElevenLabs)
- Push-to-talk mode (presiona ESPACIO)
- Continuous listening mode
- Wake word detection ("Hey ARIA")
"""

import sys
import threading
from typing import Optional, Callable


class VoiceTerminal:
    """
    Voice interface for ARIA terminal
    
    Modes:
    - Push-to-talk: Press SPACE to talk
    - Continuous: Always listening with wake word
    - Voice-only: No keyboard needed
    """
    
    def __init__(self, aria_instance, mode: str = "push-to-talk"):
        """
        Initialize voice terminal
        
        Args:
            aria_instance: ARIA instance to process commands
            mode: "push-to-talk", "continuous", or "voice-only"
        """
        self.aria = aria_instance
        self.mode = mode
        self.listening = False
        self.running = False
        
        # Initialize STT/TTS
        self._init_speech_engines()
    
    def _init_speech_engines(self):
        """Initialize speech recognition and synthesis"""
        # Speech Recognition
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.stt_available = True
            print("✅ Speech Recognition: Google (FREE)")
        except ImportError:
            self.stt_available = False
            print("❌ Speech Recognition not available. Install: pip install SpeechRecognition pyaudio")
        
        # Text-to-Speech
        try:
            from gtts import gTTS
            import pygame
            self.tts_engine = "gtts"
            self.tts_available = True
            pygame.mixer.init()
            print("✅ Text-to-Speech: gTTS (FREE)")
        except ImportError:
            try:
                import pyttsx3
                self.tts_engine = "pyttsx3"
                self.engine = pyttsx3.init()
                self.tts_available = True
                print("✅ Text-to-Speech: pyttsx3 (Offline)")
            except:
                self.tts_available = False
                print("❌ Text-to-Speech not available. Install: pip install gtts pygame")
    
    def start(self):
        """Start voice terminal"""
        if not self.stt_available:
            print("\n❌ Cannot start: Speech recognition not available")
            print("Install: pip install SpeechRecognition pyaudio")
            return
        
        self.running = True
        
        print("\n" + "=" * 60)
        print("🎤 ARIA Voice Terminal")
        print("=" * 60)
        
        if self.mode == "push-to-talk":
            self._run_push_to_talk()
        elif self.mode == "continuous":
            self._run_continuous()
        elif self.mode == "voice-only":
            self._run_voice_only()
    
    def stop(self):
        """Stop voice terminal"""
        self.running = False
        print("\n👋 Voice terminal stopped")
    
    # ==================== MODES ====================
    
    def _run_push_to_talk(self):
        """Push-to-talk mode: Press SPACE to talk"""
        print("\n📢 Mode: Push-to-Talk")
        print("Press SPACE to talk, ESC to exit\n")
        
        try:
            import keyboard
            
            while self.running:
                # Wait for SPACE key
                keyboard.wait('space')
                
                if not self.running:
                    break
                
                print("\n🎤 Listening... (release SPACE when done)")
                
                # Listen while SPACE is pressed
                audio = self._listen_once()
                
                if audio:
                    # Recognize
                    text = self._recognize_speech(audio)
                    
                    if text:
                        print(f"\n👤 You: {text}")
                        
                        # Process with ARIA
                        response = self.aria.ask(text)
                        print(f"\n🤖 ARIA: {response}")
                        
                        # Speak response
                        self._speak(response)
                
                print("\n💬 Press SPACE to talk again...")
        
        except ImportError:
            print("❌ keyboard module not available. Install: pip install keyboard")
            print("Falling back to continuous mode...")
            self._run_continuous()
        
        except KeyboardInterrupt:
            self.stop()
    
    def _run_continuous(self):
        """Continuous mode: Always listening with wake word"""
        print("\n📢 Mode: Continuous Listening")
        print("Say 'Hey ARIA' to activate, Ctrl+C to exit\n")
        
        wake_word = "hey aria"
        
        try:
            while self.running:
                print("👂 Listening for wake word...")
                
                # Listen for wake word
                audio = self._listen_once()
                text = self._recognize_speech(audio)
                
                if text and wake_word in text.lower():
                    print("\n✅ Wake word detected!")
                    self._speak("Yes?")
                    
                    # Listen for command
                    print("🎤 Listening for command...")
                    audio = self._listen_once()
                    command = self._recognize_speech(audio)
                    
                    if command:
                        print(f"\n👤 You: {command}")
                        
                        # Process with ARIA
                        response = self.aria.ask(command)
                        print(f"\n🤖 ARIA: {response}")
                        
                        # Speak response
                        self._speak(response)
        
        except KeyboardInterrupt:
            self.stop()
    
    def _run_voice_only(self):
        """Voice-only mode: No keyboard, just voice"""
        print("\n📢 Mode: Voice-Only")
        print("Just talk! Say 'exit' to quit\n")
        
        self._speak("Voice mode active. How can I help?")
        
        try:
            while self.running:
                # Listen
                audio = self._listen_once()
                text = self._recognize_speech(audio)
                
                if text:
                    print(f"\n👤 You: {text}")
                    
                    # Check for exit command
                    if "exit" in text.lower() or "quit" in text.lower():
                        self._speak("Goodbye!")
                        break
                    
                    # Process with ARIA
                    response = self.aria.ask(text)
                    print(f"\n🤖 ARIA: {response}")
                    
                    # Speak response
                    self._speak(response)
        
        except KeyboardInterrupt:
            self.stop()
    
    # ==================== SPEECH RECOGNITION ====================
    
    def _listen_once(self, timeout: int = 5) -> Optional[object]:
        """Listen for audio input once"""
        if not self.stt_available:
            return None
        
        try:
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                
                return audio
        
        except Exception as e:
            print(f"❌ Error listening: {e}")
            return None
    
    def _recognize_speech(self, audio) -> Optional[str]:
        """Recognize speech from audio"""
        if not audio:
            return None
        
        try:
            # Google Speech Recognition (FREE)
            text = self.recognizer.recognize_google(audio)
            return text
        
        except Exception as e:
            print(f"❌ Could not recognize speech: {e}")
            return None
    
    # ==================== TEXT-TO-SPEECH ====================
    
    def _speak(self, text: str):
        """Speak text using TTS"""
        if not self.tts_available:
            return
        
        try:
            if self.tts_engine == "gtts":
                self._speak_gtts(text)
            elif self.tts_engine == "pyttsx3":
                self._speak_pyttsx3(text)
        
        except Exception as e:
            print(f"❌ TTS error: {e}")
    
    def _speak_gtts(self, text: str):
        """Speak using gTTS (Google)"""
        from gtts import gTTS
        import pygame
        import tempfile
        import os
        
        # Generate audio
        tts = gTTS(text=text, lang='en')
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            temp_file = f.name
            tts.save(temp_file)
        
        # Play audio
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait for finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Cleanup
        os.unlink(temp_file)
    
    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3 (Offline)"""
        self.engine.say(text)
        self.engine.runAndWait()


# ==================== USAGE EXAMPLE ====================

def run_voice_terminal(aria_instance, mode: str = "push-to-talk"):
    """
    Run voice terminal
    
    Args:
        aria_instance: ARIA instance
        mode: "push-to-talk", "continuous", or "voice-only"
    
    Example:
        from atlas.assistants.aria import ARIA
        from aria.voice.terminal import run_voice_terminal
        
        aria = ARIA()
        run_voice_terminal(aria, mode="push-to-talk")
    """
    voice = VoiceTerminal(aria_instance, mode=mode)
    voice.start()


if __name__ == "__main__":
    print("""
    🎤 ARIA Voice Terminal
    
    Installation:
        pip install SpeechRecognition pyaudio gtts pygame keyboard
    
    Modes:
        1. Push-to-Talk (recommended)
           - Press SPACE to talk
           - Natural and controlled
        
        2. Continuous
           - Say "Hey ARIA" to activate
           - Always listening
        
        3. Voice-Only
           - No keyboard needed
           - Just talk
    
    Usage:
        from atlas.assistants.aria import ARIA
        from aria.voice.terminal import VoiceTerminal
        
        aria = ARIA()
        voice = VoiceTerminal(aria, mode="push-to-talk")
        voice.start()
    
    Keyboard Shortcuts (Push-to-Talk mode):
        SPACE - Start talking
        ESC   - Exit
    
    Voice Commands (all modes):
        "Hey ARIA" - Wake word (continuous mode)
        "exit" / "quit" - Exit voice mode
    
    ✅ Ready for voice interaction!
    """)
