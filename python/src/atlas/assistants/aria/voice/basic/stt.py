"""
Speech-to-Text using Google (FREE)
"""
class BasicSTT:
    def __init__(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.available = True
        except:
            self.available = False
    
    def listen(self) -> str:
        if not self.available:
            return ""
        # Placeholder - requires microphone setup
        return ""
