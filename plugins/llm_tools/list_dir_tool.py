import os

class ListDirTool:
    """
    Tool for listing the contents of a directory.
    Provides agents with a structural overview.
    """
    name = "list_dir"
    description = "Lists files and folders inside a given path."

    def execute(self, directory_path: str) -> str:
        try:
            items = os.listdir(directory_path)
            # Prefix folders with [DIR] and files with [FILE] for clarity
            formatted_items = []
            for item in items:
                full_path = os.path.join(directory_path, item)
                if os.path.isdir(full_path):
                    formatted_items.append(f"[DIR]  {item}")
                else:
                    formatted_items.append(f"[FILE] {item}")
                    
            return "\n".join(formatted_items)
            
        except FileNotFoundError:
            return f"Error: Directory '{directory_path}' not found."
        except Exception as e:
            return f"Error listing '{directory_path}': {str(e)}"
