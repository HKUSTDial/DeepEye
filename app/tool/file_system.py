from .base import BaseTool
from app.config import WORKSPACE_ROOT
from app.logger import logger
from pydantic import Field, model_validator, ConfigDict
from pathlib import Path
from typing import Optional, Union, List, Dict
import shutil
import json
from datetime import datetime

# Constants
FILES_ROOT = WORKSPACE_ROOT / "files"
TRASH_ROOT = WORKSPACE_ROOT / "trash"
FILES_ROOT.mkdir(parents=True, exist_ok=True)
TRASH_ROOT.mkdir(parents=True, exist_ok=True)

_FILE_SYSTEM_DESCRIPTION = """A tool to perform file operations within the workspace.
Available operations:
- load: Read file content
- write: Write content to file
- copy: Copy a file
- delete: Move file to trash
- list: Show all files in workspace
- preview: Show a sample of file content"""


class FileSystem(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "file_system"
    description: str = _FILE_SYSTEM_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "The file operation to perform",
                "enum": ["load", "write", "copy", "delete", "list", "preview"]
            },
            "file_path": {
                "type": "string",
                "description": "Target file path relative to workspace/files/. No parent directory traversal allowed."
            },
            "content": {
                "type": "string",
                "description": "Content to write (required for write operation)"
            },
            "source_path": {
                "type": "string",
                "description": "Source file path for copy operation, relative to workspace/files/"
            },
            "preview_length": {
                "type": "integer",
                "description": "Number of characters to preview (default 200 for preview operation)",
                "minimum": 1,
                "maximum": 1000
            }
        },
        "required": ["operation"],
        "additionalProperties": False
    }

    def _validate_path(self, file_path: Union[str, Path], allow_trash: bool = False) -> Path:
        """Validate and resolve a file path to ensure it MUST be within FILES_ROOT or TRASH_ROOT.
        If allow_trash is True, the path can be within TRASH_ROOT."""
        try:
            if allow_trash and str(file_path).startswith("trash/"):
                base = WORKSPACE_ROOT
                file_path = Path(file_path)
            else:
                base = FILES_ROOT
                file_path = Path(file_path)
            
            path = base / file_path
            resolved = path.resolve()
            allowed_roots = [str(FILES_ROOT)]
            if allow_trash:
                allowed_roots.append(str(TRASH_ROOT))
            if not any(str(resolved).startswith(root) for root in allowed_roots):
                raise ValueError(f"Path {file_path} attempts to escape workspace")
            return resolved
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise ValueError(f"Invalid path {file_path}: {e}")

    async def load_file(self, file_path: str) -> str:
        """Load file content as string."""
        path = self._validate_path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise

    async def write_file(self, file_path: str, content: str) -> str:
        """Write content to file, create parent dirs if needed."""
        path = self._validate_path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {file_path}"
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise

    async def copy_file(self, source_path: str, file_path: str) -> str:
        """Copy file from source to destination."""
        src = self._validate_path(source_path)
        dst = self._validate_path(file_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return f"Successfully copied {source_path} to {file_path}"
        except Exception as e:
            logger.error(f"Error copying file from {source_path} to {file_path}: {e}")
            raise

    async def delete_file(self, file_path: str) -> str:
        """Move file to trash instead of permanent deletion."""
        path = self._validate_path(file_path)        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path exists but is not a file: {file_path}")
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = path.name
            trash_name = f"{filename}.{timestamp}"
            trash_path = TRASH_ROOT / trash_name
            
            # Move to trash (soft delete) and create .trashinfo file with original path and deletion time (for recovery)
            shutil.move(str(path), str(trash_path))
            info = {
                "original_path": str(path.relative_to(FILES_ROOT)),
                "deletion_time": datetime.now().isoformat(),
            }
            with open(f"{trash_path}.info", 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)
            return f"File {file_path} has been moved to trash as {trash_name}"
        except Exception as e:
            logger.error(f"Error moving file {file_path} to trash: {e}")
            raise

    async def list_files(self) -> str:
        """List all files in the workspace with their sizes and modification times."""
        try:
            files = []
            for path in FILES_ROOT.rglob('*'):
                if path.is_file():
                    rel_path = path.relative_to(FILES_ROOT)
                    stat = path.stat()
                    files.append({
                        'path': str(rel_path),
                        'size': self._format_size(stat.st_size),
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
            if not files:
                return "No files found in workspace."
            output = ["Files in workspace:"]
            for f in sorted(files, key=lambda x: x['path']):
                output.append(f"- {f['path']} ({f['size']}, modified: {f['modified']})")
            # # Add trash info if exists
            # trash_files = list(TRASH_ROOT.glob('*'))
            # if trash_files:
            #     output.append("\nFiles in trash:")
            #     for path in trash_files:
            #         if path.suffix != '.info':  # Skip .info files
            #             output.append(f"- {path.name}")
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

    async def preview_file(self, file_path: str, preview_length: int = 200) -> str:
        """Show a preview of file content with size and stats."""
        path = self._validate_path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        try:
            stat = path.stat()
            size = self._format_size(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read(preview_length)
                has_more = len(content) == preview_length
            output = [
                f"File: {file_path}",
                f"Size: {size}",
                f"Modified: {modified}",
                "\nPreview:",
                content,
            ]
            if has_more:
                output.append("\n... (content continues)")
            return "\n".join(output)
        except Exception as e:
            logger.error(f"Error previewing file {file_path}: {e}")
            raise

    def _format_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    async def execute(self, operation: str, file_path: Optional[str] = None, 
                     content: Optional[str] = None, source_path: Optional[str] = None,
                     preview_length: Optional[int] = None) -> str:
        """Execute the requested file operation."""
        try:
            match operation:
                case "list":
                    return await self.list_files()
                case "write":
                    if file_path is None:
                        raise ValueError("file_path is required for write operation")
                    if content is None:
                        raise ValueError("content is required for write operation")
                    return await self.write_file(file_path, content)
                case "copy":
                    if file_path is None:
                        raise ValueError("file_path is required for copy operation")
                    if source_path is None:
                        raise ValueError("source_path is required for copy operation")
                    return await self.copy_file(source_path, file_path)
                case "preview":
                    if file_path is None:
                        raise ValueError("file_path is required for preview operation")
                    return await self.preview_file(file_path, preview_length or 200)
                case "load":
                    if file_path is None:
                        raise ValueError("file_path is required for load operation")
                    return await self.load_file(file_path)
                case "delete":
                    if file_path is None:
                        raise ValueError("file_path is required for delete operation")
                    return await self.delete_file(file_path)
                case _:
                    raise ValueError(f"Unknown operation: {operation}")      
        except Exception as e:
            error_msg = f"File operation {operation} failed: {str(e)}"
            logger.error(error_msg)
            return error_msg



if __name__ == "__main__":
    import asyncio
    
    async def test_file_system():
        fs = FileSystem()
        
        # Test write
        write_result = await fs.execute(
            operation="write",
            file_path="test/hello.txt",
            content="Hello, World!\n" * 10
        )
        print("\nWrite:", write_result)
        
        # Test list
        list_result = await fs.execute(operation="list")
        print("\nList:", list_result)
        
        # Test preview
        preview_result = await fs.execute(
            operation="preview",
            file_path="test/hello.txt",
            preview_length=50
        )
        print("\nPreview:", preview_result)
        
        # Test copy
        copy_result = await fs.execute(
            operation="copy",
            file_path="test/hello_backup.txt",
            source_path="test/hello.txt"
        )
        print("\nCopy:", copy_result)
        
        # Test delete (moves to trash)
        delete_result = await fs.execute(
            operation="delete",
            file_path="test/hello.txt"
        )
        print("\nDelete:", delete_result)
        
        # Show final state
        final_list = await fs.execute(operation="list")
        print("\nFinal state:", final_list)
    
    asyncio.run(test_file_system())