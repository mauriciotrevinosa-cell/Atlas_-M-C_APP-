import sys
import os

# Add python/src to path
sys.path.append(os.path.join(os.getcwd(), 'python', 'src'))

from atlas.assistants.aria import create_aria

def main():
    # Banner will be printed by ARIA init
    try:
        aria = create_aria()
        print("\n(Type 'quit' to exit)")
        print("----------------------------------------")
        
        while True:
            user_input = input("\n👤 You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
                
            print("🤖 ARIA: Thinking...", end='\r')
            response = aria.ask(user_input)
            print(f"🤖 ARIA: {response}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Tip: Make sure Ollama is running!")

if __name__ == "__main__":
    main()
