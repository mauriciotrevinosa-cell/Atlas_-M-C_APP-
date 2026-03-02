import sys
import os

# Ensure we can find the project modules
current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, "python", "src"))
sys.path.append(os.path.join(current_dir, "apps", "server"))

try:
    from atlas.assistants.aria import ARIA
    from server import run_server
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        # Clear screen for cleaner look
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Initialize ARIA core (Using 1B model for speed/memory)
        aria = ARIA(model="llama3.2:1b")
        
        # Start the server (Modified to not print redundant headers if possible, or we accept the secondary header)
        print("\n" + "="*60)
        print("🌐 Starting Multi-Device Server Layer...")
        print("="*60 + "\n")
        
        run_server(aria, host="127.0.0.1", port=8080)
        
    except Exception as e:
        print(f"\n❌ Server Error: {e}")
        input("Press Enter to exit...")
