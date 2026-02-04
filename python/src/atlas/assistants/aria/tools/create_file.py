"""
ARIA Create File Tool

Create files in the filesystem
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional


class CreateFileTool:
    """
    Create files in filesystem
    
    Features:
    - Create text files
    - Create directories if needed
    - Overwrite protection
    - File validation
    """
    
    name = "create_file"
    description = "Create files in the filesystem with specified content"
    
    def __init__(self, base_dir: str = "outputs"):
        """
        Initialize create file tool
        
        Args:
            base_dir: Base directory for file creation (default: "outputs")
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def execute(self,
                filename: str,
                content: str,
                directory: Optional[str] = None,
                overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a file
        
        Args:
            filename: Name of file to create
            content: Content to write
            directory: Subdirectory (relative to base_dir)
            overwrite: Whether to overwrite if exists
        
        Returns:
            Dict with result
        """
        try:
            # Construct full path
            if directory:
                target_dir = self.base_dir / directory
                target_dir.mkdir(parents=True, exist_ok=True)
            else:
                target_dir = self.base_dir
            
            filepath = target_dir / filename
            
            # Check if exists
            if filepath.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"File already exists: {filepath}. Use overwrite=True to replace.",
                    "filepath": str(filepath)
                }
            
            # Write file
            filepath.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "filepath": str(filepath),
                "size": len(content),
                "message": f"File created: {filepath}"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create file: {str(e)}"
            }
    
    def create_markdown(self,
                       filename: str,
                       title: str,
                       content: str,
                       directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Create markdown file with header
        
        Args:
            filename: Filename (should end in .md)
            title: Document title
            content: Document content
            directory: Subdirectory
        
        Returns:
            Dict with result
        """
        if not filename.endswith('.md'):
            filename += '.md'
        
        markdown_content = f"# {title}\n\n{content}"
        
        return self.execute(filename, markdown_content, directory)
    
    def create_json(self,
                   filename: str,
                   data: Dict,
                   directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Create JSON file
        
        Args:
            filename: Filename (should end in .json)
            data: Dict to serialize
            directory: Subdirectory
        
        Returns:
            Dict with result
        """
        import json
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        json_content = json.dumps(data, indent=2)
        
        return self.execute(filename, json_content, directory)
    
    def get_parameters_schema(self) -> Dict:
        """Get tool parameter schema"""
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of file to create (with extension)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to file"
                },
                "directory": {
                    "type": "string",
                    "description": "Subdirectory (optional)"
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Overwrite if exists (default: false)",
                    "default": False
                }
            },
            "required": ["filename", "content"]
        }


if __name__ == "__main__":
    # Test
    print("Testing CreateFileTool...")
    print("=" * 60)
    
    tool = CreateFileTool(base_dir="test_outputs")
    
    # Test 1: Create simple text file
    print("\nTest 1: Create text file")
    result = tool.execute(
        filename="test.txt",
        content="Hello, World!\nThis is a test file."
    )
    
    if result["success"]:
        print(f"✅ {result['message']}")
        print(f"   Size: {result['size']} bytes")
    else:
        print(f"❌ {result['error']}")
    
    # Test 2: Create markdown
    print("\n" + "=" * 60)
    print("Test 2: Create markdown")
    result = tool.create_markdown(
        filename="report",
        title="Test Report",
        content="This is a test report.\n\n## Section 1\n\nContent here."
    )
    
    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['error']}")
    
    # Test 3: Create JSON
    print("\n" + "=" * 60)
    print("Test 3: Create JSON")
    result = tool.create_json(
        filename="data",
        data={"name": "ARIA", "version": "3.0", "complete": True}
    )
    
    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['error']}")
    
    # Test 4: Try to overwrite (should fail)
    print("\n" + "=" * 60)
    print("Test 4: Overwrite protection")
    result = tool.execute(
        filename="test.txt",
        content="New content"
    )
    
    if not result["success"]:
        print(f"✅ Protection worked: {result['error']}")
    else:
        print(f"❌ Should have failed")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
