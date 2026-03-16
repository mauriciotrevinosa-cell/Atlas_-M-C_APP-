"""
Text-to-Speech using gTTS (FREE)
"""
class BasicTTS:
    def __init__(self):
        try:
            from gtts import gTTS
            self.available = True
        except ImportError:
            self.available = False
    
    def speak(self, text: str):
        if not self.available:
            print(text)
