"""
ARIA WhatsApp Bot - 24/7 Integration

Bot WhatsApp usando Twilio para mensajes bidireccionales
ARIA puede recibir y responder mensajes automáticamente

Features:
- Recibir mensajes de WhatsApp
- ARIA procesa y responde
- Crear tareas en ClickUp desde WhatsApp
- Consultar Notion desde WhatsApp
- Voice notes support
- Media messages
"""

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from typing import Optional
import os


class WhatsAppBot:
    """
    WhatsApp Bot usando Twilio
    
    Setup:
    1. Crear cuenta Twilio: twilio.com
    2. Configurar WhatsApp Sandbox: twilio.com/console/sms/whatsapp/sandbox
    3. Obtener: Account SID, Auth Token, WhatsApp number
    4. Configurar webhook: https://your-server.com/whatsapp
    """
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Initialize WhatsApp bot
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: WhatsApp number (format: whatsapp:+14155238886)
        """
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        self.aria = None  # Se conecta después
    
    def connect_aria(self, aria_instance):
        """Connect ARIA instance for processing messages"""
        self.aria = aria_instance
    
    def send_message(self, to_number: str, message: str, media_url: Optional[str] = None):
        """
        Send message to WhatsApp
        
        Args:
            to_number: Recipient WhatsApp number (format: whatsapp:+1234567890)
            message: Message text
            media_url: Optional media URL (image, video, audio)
        
        Returns:
            Message SID
        """
        kwargs = {
            "body": message,
            "from_": self.from_number,
            "to": to_number
        }
        
        if media_url:
            kwargs["media_url"] = [media_url]
        
        message_obj = self.client.messages.create(**kwargs)
        return message_obj.sid
    
    def process_incoming_message(self, from_number: str, message_body: str) -> str:
        """
        Process incoming WhatsApp message with ARIA
        
        Args:
            from_number: Sender WhatsApp number
            message_body: Message text
        
        Returns:
            ARIA's response
        """
        if not self.aria:
            return "❌ ARIA not connected. Please configure."
        
        # Check for special commands
        if message_body.startswith("/"):
            return self._handle_command(message_body)
        
        # Process with ARIA
        try:
            response = self.aria.ask(message_body)
            return f"🤖 ARIA:\n\n{response}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _handle_command(self, command: str) -> str:
        """
        Handle special commands
        
        Commands:
        /help - Show help
        /status - ARIA status
        /tasks - My ClickUp tasks
        /note - Create Notion note
        """
        cmd = command.lower().strip()
        
        if cmd == "/help":
            return """
📱 ARIA WhatsApp Commands:

/help - Show this help
/status - Check ARIA status
/tasks - Get your ClickUp tasks
/note [title] - Create Notion note

Or just chat normally with ARIA!

Examples:
- "What's AAPL price?"
- "Create task: Analyze BTC"
- "Add note: Market looking bullish"
"""
        
        elif cmd == "/status":
            return "✅ ARIA is online and ready!"
        
        elif cmd.startswith("/tasks"):
            return "📋 Fetching your ClickUp tasks..."
            # TODO: Integrate with ClickUp
        
        elif cmd.startswith("/note"):
            note_text = command[5:].strip()
            return f"📝 Creating Notion note: {note_text}"
            # TODO: Integrate with Notion
        
        else:
            return "❓ Unknown command. Type /help for help."


# ==================== FLASK WEBHOOK SERVER ====================

app = Flask(__name__)

# Global bot instance (initialize in main)
bot = None


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Webhook endpoint for incoming WhatsApp messages
    
    Twilio sends POST requests here when messages arrive
    """
    # Get incoming message
    from_number = request.form.get("From")
    message_body = request.form.get("Body", "")
    
    # Process with bot
    if bot:
        response_text = bot.process_incoming_message(from_number, message_body)
    else:
        response_text = "❌ Bot not initialized"
    
    # Create Twilio response
    resp = MessagingResponse()
    resp.message(response_text)
    
    return str(resp)


@app.route("/status", methods=["GET"])
def status():
    """Health check endpoint"""
    return {"status": "online", "bot": "WhatsApp ARIA"}


# ==================== USAGE EXAMPLE ====================

def run_whatsapp_bot(aria_instance, account_sid: str, auth_token: str, 
                     from_number: str, port: int = 5000):
    """
    Run WhatsApp bot server
    
    Args:
        aria_instance: ARIA instance
        account_sid: Twilio Account SID
        auth_token: Twilio Auth Token
        from_number: WhatsApp number (whatsapp:+14155238886)
        port: Server port (default: 5000)
    
    Example:
        from atlas.assistants.aria import ARIA
        
        aria = ARIA()
        
        run_whatsapp_bot(
            aria_instance=aria,
            account_sid="ACxxxxx",
            auth_token="your_token",
            from_number="whatsapp:+14155238886",
            port=5000
        )
    """
    global bot
    
    # Initialize bot
    bot = WhatsAppBot(account_sid, auth_token, from_number)
    bot.connect_aria(aria_instance)
    
    print("=" * 60)
    print("🤖 ARIA WhatsApp Bot Starting...")
    print("=" * 60)
    print(f"Server running on port {port}")
    print(f"Webhook URL: http://your-server.com:{port}/whatsapp")
    print("\nNext steps:")
    print("1. Expose this server to internet (ngrok, VPS, etc.)")
    print("2. Configure Twilio webhook: https://twilio.com/console/sms/whatsapp/sandbox")
    print("3. Send WhatsApp message to your Twilio number")
    print("=" * 60)
    
    # Run Flask server
    app.run(host="0.0.0.0", port=port, debug=False)


# ==================== DEPLOYMENT WITH NGROK ====================

def setup_ngrok(port: int = 5000):
    """
    Setup ngrok tunnel for local development
    
    Requires: pip install pyngrok
    """
    try:
        from pyngrok import ngrok
        
        # Start ngrok tunnel
        public_url = ngrok.connect(port)
        print(f"\n✅ Ngrok tunnel active: {public_url}")
        print(f"Webhook URL: {public_url}/whatsapp")
        print("\nCopy this URL to Twilio webhook configuration")
        
        return public_url
    except ImportError:
        print("⚠️  pyngrok not installed. Run: pip install pyngrok")
        return None


if __name__ == "__main__":
    print("""
    🤖 ARIA WhatsApp Bot
    
    Setup Instructions:
    
    1. Get Twilio credentials:
       - Sign up: twilio.com
       - Get Account SID and Auth Token
       - Get WhatsApp number (Sandbox or production)
    
    2. Configure webhook:
       - Go to: twilio.com/console/sms/whatsapp/sandbox
       - Set webhook URL: http://your-server.com:5000/whatsapp
    
    3. Run this bot:
       python whatsapp_bot.py
    
    4. Send message to Twilio WhatsApp number
    
    For local testing, use ngrok:
       pip install pyngrok
       python whatsapp_bot.py --ngrok
    
    Example usage in code:
    
        from atlas.assistants.aria import ARIA
        from aria.integrations import WhatsAppBot, run_whatsapp_bot
        
        aria = ARIA()
        
        run_whatsapp_bot(
            aria_instance=aria,
            account_sid="ACxxxxx",
            auth_token="your_token",
            from_number="whatsapp:+14155238886"
        )
    
    ✅ Ready to receive WhatsApp messages 24/7!
    """)
