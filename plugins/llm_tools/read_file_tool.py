class ReadFileTool:
    """
    Tool for reading a local file.
    In Phase 1, it allows agents to inspect code files.
    """
    name = "read_file"
    description = "Reads the entire content of a specified file. Do not use for very large files."

    def execute(self, file_path: str) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found."
        except Exception as e:
            return f"Error reading '{file_path}': {str(e)}"
