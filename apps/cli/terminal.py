"""
ARIA Interactive Terminal - 100% Autonomous

Terminal conversacional usando:
- Ollama (local LLM)
- System prompts profesionales
- Tool calling patterns
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add python/src directory to path
# File is in apps/cli/terminal.py -> need to go up 3 levels to root, then python/src
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "python" / "src"))

from atlas.assistants.aria.core.chat import ARIA
from atlas.assistants.aria.tools.quantum_compute import QuantumComputeTool
from atlas.assistants.aria.tools.get_data import GetDataTool
from atlas.assistants.aria.tools.web_search import WebSearchTool
from atlas.assistants.aria.tools.create_file import CreateFileTool
from atlas.assistants.aria.tools.execute_code import ExecuteCodeTool
from atlas.assistants.aria.tools.get_market_state import GetMarketStateTool
from atlas.assistants.aria.tools.analyze_risk import AnalyzeRiskTool
from atlas.assistants.aria.tools.run_backtest import RunBacktestTool
from atlas.assistants.aria.tools.explain_signal import ExplainSignalTool

class ARIATerminal:
    """
    Terminal interactiva para ARIA
    
    Comandos:
    - /exit, /quit - Salir
    - /clear - Limpiar historial
    - /save - Guardar conversación
    - /help - Mostrar ayuda
    """
    
    def __init__(self):
        """Initialize terminal"""
        self.aria = None
        self.session_start = datetime.now()
    
    def print_banner(self):
        """Print welcome banner"""
        banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     █████╗ ██████╗ ██╗ █████╗                            ║
║    ██╔══██╗██╔══██╗██║██╔══██╗                           ║
║    ███████║██████╔╝██║███████║                           ║
║    ██╔══██║██╔══██╗██║██╔══██║                           ║
║    ██║  ██║██║  ██║██║██║  ██║                           ║
║    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝                           ║
║                                                          ║
║    Atlas Reasoning & Intelligence Assistant              ║
║    v2.0 - Autonomous Edition                             ║
║    100% Local | Powered by Ollama                        ║
║    Product by M&C © 2026                                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Sistema: 100% Local
Modelo: llama3.1:8b
Estado: Listo para asistir

Escribe /help para ver comandos disponibles
Escribe /exit para salir
"""
        print(banner)
    
    def print_help(self):
        """Print help message"""
        help_text = """
╔══════════════════════════════════════════════════════════╗
║  COMANDOS DISPONIBLES                                    ║
╚══════════════════════════════════════════════════════════╝

Comandos especiales:
  /exit, /quit     - Salir del terminal
  /clear           - Limpiar historial de conversación
  /save [nombre]   - Guardar conversación actual
  /help            - Mostrar esta ayuda
  /stats           - Ver estadísticas de la sesión

Uso normal:
  - Escribe tu pregunta y presiona Enter
  - ARIA responderá usando su conocimiento y análisis
"""
        print(help_text)
    
    def print_stats(self):
        """Print session statistics"""
        if not self.aria:
            print("\\n⚠️ ARIA no está inicializada\\n")
            return
        
        duration = datetime.now() - self.session_start
        messages = len(self.aria.history)
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║  ESTADÍSTICAS DE SESIÓN                                  ║
╚══════════════════════════════════════════════════════════╝

Inicio: {self.session_start.strftime("%H:%M:%S")}
Duración: {duration.seconds // 60} minutos
Mensajes: {messages}
Backend: {self.aria.backend}
Modelo: {self.aria.model}
""")
    
    def save_conversation(self, filename: str = None):
        """Save conversation to file"""
        if not self.aria or not self.aria.history:
            print("\\n⚠️ No hay conversación para guardar\\n")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = Path("conversations") / filename
        filepath.parent.mkdir(exist_ok=True)
        
        self.aria.export_conversation(str(filepath))
        print(f"\\n✅ Conversación guardada: {filepath}\\n")
    
    def run(self):
        """Run the terminal"""
        self.print_banner()
        
        # Initialize ARIA
        print("🔄 Inicializando ARIA (Project Manager Mode)...\\n")
        try:
            self.aria = ARIA(model="llama3.1:8b")
            
            # Register Core Tools
            self.aria.register_tool(GetDataTool())
            self.aria.register_tool(WebSearchTool())
            self.aria.register_tool(CreateFileTool())
            self.aria.register_tool(ExecuteCodeTool())
            self.aria.register_tool(GetMarketStateTool())
            self.aria.register_tool(QuantumComputeTool())
            self.aria.register_tool(AnalyzeRiskTool())
            self.aria.register_tool(RunBacktestTool())
            self.aria.register_tool(ExplainSignalTool())
            
            print("✅ ARIA lista (9 tools cargadas)\n")
            print("🤖 ¡Hola! Soy ARIA. ¿En qué puedo ayudarte hoy?\\n")
        except Exception as e:
            print(f"❌ Error inicializando ARIA: {e}")
            print("\\n⚠️ Asegúrate de que Ollama está corriendo:")
            print("   1. Ejecuta: ollama serve")
            return
        
        # Main loop
        while True:
            try:
                user_input = input("\\n Mauri: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/'):
                    command_parts = user_input.split(maxsplit=1)
                    command = command_parts[0].lower()
                    args = command_parts[1] if len(command_parts) > 1 else None
                    
                    if command in ['/exit', '/quit']:
                        print("\\n👋 ¡Hasta Luego!\\n")
                        break
                    elif command == '/clear':
                        self.aria.reset()
                        print("\\n✅ Historial limpiado\\n")
                        continue
                    elif command == '/save':
                        self.save_conversation(args)
                        continue
                    elif command == '/help':
                        self.print_help()
                        continue
                    elif command == '/stats':
                        self.print_stats()
                        continue
                    else:
                        print(f"\\n⚠️ Comando desconocido: {command}")
                        continue
                
                print("\\n🤖 ARIA: ", end="", flush=True)
                print("(pensando...)", end="", flush=True)

                try:
                    response = self.aria.ask(user_input)
                    print("\\r🤖 ARIA: " + " " * 20 + "\\r🤖 ARIA: ", end="", flush=True)
                    print(response)
                except KeyboardInterrupt:
                    print("\\n\\n⚠️ Respuesta interrumpida\\n")
                    continue
                except Exception as e:
                    print(f"\\n❌ Error: {e}\\n")
                    continue
            
            except KeyboardInterrupt:
                print("\\n\\n👋 ¡Hasta luego!\\n")
                break
            except EOFError:
                break

if __name__ == "__main__":
    ARIATerminal().run()
