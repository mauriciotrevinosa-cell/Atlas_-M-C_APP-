"""
ARIA Read File Tool

Read files from filesystem
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class ReadFileTool:
    """
    Read files from filesystem
    
    Features:
    - Read text files
    - Read binary files (as base64)
    - Line limits for large files
    - Multiple file formats
    """
    
    name = "read_file"
    description = "Read files from the filesystem"
    
    def __init__(self, base_dir: str = "."):
        """
        Initialize read file tool
        
        Args:
            base_dir: Base directory for file reading
        """
        self.base_dir = Path(base_dir).resolve()

    def _resolve_path(self, filepath: str) -> Path:
        """
        Resolve and validate a path against the configured base directory.
        """
        resolved = (self.base_dir / filepath).resolve()
        if not resolved.is_relative_to(self.base_dir):
            raise ValueError(f"Path escapes base directory: {filepath}")
        return resolved
    
    def execute(self,
                filepath: str,
                max_lines: Optional[int] = None,
                encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read a file
        
        Args:
            filepath: Path to file (relative to base_dir)
            max_lines: Maximum lines to read (None = all)
            encoding: File encoding (default: utf-8)
        
        Returns:
            Dict with file content
        """
        try:
            full_path = self._resolve_path(filepath)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {full_path}"
                }

            if full_path.is_dir():
                entries = []
                for item in sorted(full_path.iterdir()):
                    entries.append(
                        {
                            "name": item.name,
                            "path": str(item.relative_to(self.base_dir)),
                            "type": "directory" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else None,
                        }
                    )
                return {
                    "success": True,
                    "filepath": str(full_path),
                    "is_directory": True,
                    "entries": entries,
                    "count": len(entries),
                }
            
            # Check if file is too large
            file_size = full_path.stat().st_size
            
            if file_size > 10 * 1024 * 1024:  # 10 MB
                return {
                    "success": False,
                    "error": f"File too large: {file_size / 1024 / 1024:.1f} MB (max: 10 MB)"
                }
            
            # Read file
            if max_lines:
                lines = []
                truncated = False
                with open(full_path, 'r', encoding=encoding) as f:
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            truncated = True
                            break
                        lines.append(line.rstrip('\n'))
                
                content = '\n'.join(lines)
            else:
                content = full_path.read_text(encoding=encoding)
                truncated = False
            
            return {
                "success": True,
                "filepath": str(full_path),
                "content": content,
                "size": file_size,
                "lines": content.count('\n') + 1,
                "truncated": truncated
            }
        
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"Cannot decode file with encoding: {encoding}. File might be binary."
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }
    
    def read_json(self, filepath: str) -> Dict[str, Any]:
        """
        Read JSON file
        
        Args:
            filepath: Path to JSON file
        
        Returns:
            Dict with parsed JSON
        """
        import json
        
        result = self.execute(filepath)
        
        if not result["success"]:
            return result
        
        try:
            data = json.loads(result["content"])
            
            return {
                "success": True,
                "filepath": result["filepath"],
                "data": data,
                "type": "json"
            }
        
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {str(e)}"
            }
    
    def list_files(self,
                   directory: str = ".",
                   pattern: str = "*",
                   recursive: bool = False) -> Dict[str, Any]:
        """
        List files in directory
        
        Args:
            directory: Directory to list
            pattern: File pattern (e.g., "*.py")
            recursive: Search recursively
        
        Returns:
            Dict with file list
        """
        try:
            dir_path = self._resolve_path(directory)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {dir_path}"
                }
            
            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {dir_path}"
                }
            
            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))
            
            file_list = []
            for f in files:
                if f.is_file():
                    file_list.append({
                        "name": f.name,
                        "path": str(f.relative_to(self.base_dir)),
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime
                    })
            
            return {
                "success": True,
                "directory": str(dir_path),
                "pattern": pattern,
                "files": file_list,
                "count": len(file_list)
            }
        
        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list files: {str(e)}"
            }
    
    def get_parameters_schema(self) -> Dict:
        """Get tool parameter schema"""
        return {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Path to file to read"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to read (optional)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding",
                    "default": "utf-8"
                }
            },
            "required": ["filepath"]
        }


if __name__ == "__main__":
    # Test
    print("Testing ReadFileTool...")
    print("=" * 60)
    
    # First create a test file
    test_file = Path("test_read.txt")
    test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    
    tool = ReadFileTool(base_dir=".")
    
    # Test 1: Read full file
    print("\nTest 1: Read full file")
    result = tool.execute("test_read.txt")
    
    if result["success"]:
        print(f"✅ Read {result['lines']} lines ({result['size']} bytes)")
        print(f"Content:\n{result['content']}")
    else:
        print(f"❌ {result['error']}")
    
    # Test 2: Read with line limit
    print("\n" + "=" * 60)
    print("Test 2: Read with line limit")
    result = tool.execute("test_read.txt", max_lines=3)
    
    if result["success"]:
        print(f"✅ Read {result['lines']} lines (truncated: {result['truncated']})")
        print(f"Content:\n{result['content']}")
    else:
        print(f"❌ {result['error']}")
    
    # Test 3: File not found
    print("\n" + "=" * 60)
    print("Test 3: File not found")
    result = tool.execute("nonexistent.txt")
    
    if not result["success"]:
        print(f"✅ Error caught: {result['error']}")
    else:
        print(f"❌ Should have failed")
    
    # Cleanup
    test_file.unlink()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
