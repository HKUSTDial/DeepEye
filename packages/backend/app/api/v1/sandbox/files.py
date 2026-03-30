"""Sandbox file management API"""

import base64
import io
import shlex
import zipfile
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from deepeye.utils.logger import logger
from app.sandbox import sandbox_manager

router = APIRouter(prefix="/files", tags=["sandbox-files"])


def _sh_quote(value: str) -> str:
    return shlex.quote(value)


def _join_path(parent: str, name: str) -> str:
    normalized_parent = parent.rstrip("/")
    if not normalized_parent:
        return f"/{name}"
    return f"{normalized_parent}/{name}"


async def _get_existing_sandbox(session_id: str):
    sandbox = await sandbox_manager.get_sandbox(session_id)
    if not sandbox:
        logger.warning(f"[SandboxFiles] No sandbox found for session {session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"No sandbox found for session {session_id}",
        )
    return sandbox


class FileInfo(BaseModel):
    """File information"""
    name: str
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    extension: Optional[str] = None


class FileListResponse(BaseModel):
    """File list response"""
    session_id: str
    files: List[FileInfo]


class FileContentResponse(BaseModel):
    """File content response"""
    path: str
    content: str
    content_type: str  # "text", "binary", "image"
    encoding: str  # "utf-8", "base64"


class FileWriteRequest(BaseModel):
    """File write request"""
    path: str
    content: str


@router.get("/sessions/{session_id}/list", response_model=FileListResponse)
async def list_files(session_id: str, path: str = "/workspace"):
    """
    List files in sandbox workspace.
    
    Args:
        session_id: Session ID
        path: Directory path (default: /workspace)
        
    Returns:
        List of files and directories
    """
    try:
        sandbox = await _get_existing_sandbox(session_id)
        qpath = _sh_quote(path)
        
        # Check if path exists and is a directory
        check_cmd = f"test -d {qpath} && echo 'exists'"
        check_result = await sandbox.exec_command(check_cmd)
        if not check_result.success or "exists" not in check_result.stdout:
            logger.info(f"[SandboxFiles] Path {path} does not exist or is not a directory, returning empty list")
            return FileListResponse(session_id=session_id, files=[])
        
        # Use null-delimited output so tabs/newlines in filenames don't corrupt parsing.
        cmd = f"find {qpath} -maxdepth 1 ! -path {qpath} -printf '%f\\0%y\\0%s\\0' 2>/dev/null"
        logger.info(f"[SandboxFiles] Executing: {cmd}")
        result = await sandbox.exec_command(cmd)
        logger.info(f"[SandboxFiles] Result - success: {result.success}, stdout: {result.stdout[:300]}")
        
        if not result.success:
            logger.error(f"[SandboxFiles] Command failed - stderr: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list files: {result.stderr}"
            )
        
        # Parse null-delimited output in name/type/size triplets.
        files = []
        entries = result.stdout.split("\0")
        if entries and entries[-1] == "":
            entries.pop()
        for i in range(0, len(entries), 3):
            triplet = entries[i:i + 3]
            if len(triplet) != 3:
                logger.warning(f"[SandboxFiles] Skipping incomplete entry at offset {i}: {triplet!r}")
                continue

            name, ftype, size_str = triplet
            file_type = "directory" if ftype == 'd' else "file"
            file_path = _join_path(path, name)
            
            # Get file extension for files
            extension = None
            if file_type == "file" and '.' in name:
                extension = name.rsplit('.', 1)[1]
            
            # Parse size (only for files)
            size = None
            if file_type == "file":
                try:
                    size = int(size_str)
                except ValueError:
                    pass
            
            files.append(FileInfo(
                name=name,
                path=file_path,
                type=file_type,
                size=size,
                extension=extension
            ))
        
        # Sort: directories first, then files
        files.sort(key=lambda x: (x.type == "file", x.name.lower()))
        
        logger.info(f"[SandboxFiles] Successfully listed {len(files)} items for {session_id}:{path}")
        return FileListResponse(
            session_id=session_id,
            files=files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[SandboxFiles] Error listing files: {e}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/sessions/{session_id}/content", response_model=FileContentResponse)
async def get_file_content(session_id: str, path: str):
    """
    Get file content from sandbox.
    
    Args:
        session_id: Session ID
        path: File path
        
    Returns:
        File content (text or base64 encoded)
    """
    try:
        sandbox = await _get_existing_sandbox(session_id)
        
        # Check if file exists
        qpath = _sh_quote(path)
        check_result = await sandbox.exec_command(f"test -f {qpath} && echo 'exists'")
        if not check_result.success or 'exists' not in check_result.stdout:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {path}"
            )
        
        # Determine file type by extension
        extension = path.split('.')[-1].lower() if '.' in path else ''
        
        # Text file extensions
        text_extensions = {
            'txt', 'py', 'js', 'ts', 'jsx', 'tsx', 'json', 'xml', 'html', 'css',
            'md', 'yaml', 'yml', 'toml', 'ini', 'conf', 'sh', 'bash',
            'csv', 'tsv', 'log', 'sql', 'r', 'java', 'c', 'cpp', 'h', 'go'
        }
        
        # Image extensions
        image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp', 'ico'}
        
        if extension in text_extensions:
            # Read as text
            result = await sandbox.exec_command(f"cat {qpath}")
            if not result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read file: {result.stderr}"
                )
            
            return FileContentResponse(
                path=path,
                content=result.stdout,
                content_type="text",
                encoding="utf-8"
            )
            
        elif extension in image_extensions:
            # Read as base64
            result = await sandbox.exec_command(f"base64 {qpath}")
            if not result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read file: {result.stderr}"
                )
            
            return FileContentResponse(
                path=path,
                content=result.stdout.strip(),
                content_type="image",
                encoding="base64"
            )
            
        else:
            # Try to read as text, fallback to base64
            result = await sandbox.exec_command(f"file -b --mime-type {qpath}")
            mime_type = result.stdout.strip() if result.success else ""
            
            if 'text' in mime_type or not mime_type:
                # Try text
                result = await sandbox.exec_command(f"cat {qpath}")
                if result.success:
                    return FileContentResponse(
                        path=path,
                        content=result.stdout,
                        content_type="text",
                        encoding="utf-8"
                    )
            
            # Fallback to base64
            result = await sandbox.exec_command(f"base64 {qpath}")
            if not result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read file: {result.stderr}"
                )
            
            return FileContentResponse(
                path=path,
                content=result.stdout.strip(),
                content_type="binary",
                encoding="base64"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SandboxFiles] Error reading file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/sessions/{session_id}/write")
async def write_file(session_id: str, payload: FileWriteRequest):
    """
    Write content to file in sandbox.
    
    Args:
        session_id: Session ID
        path: File path
        content: File content
        
    Returns:
        Success message
    """
    try:
        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        if not sandbox:
            raise HTTPException(
                status_code=404,
                detail=f"No sandbox found for session {session_id}"
            )
        
        path = payload.path
        content = payload.content
        await sandbox.write_text_file(path, content)
        
        logger.info(f"[SandboxFiles] Written file: {path} for session {session_id}")
        
        return {"status": "success", "path": path}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SandboxFiles] Error writing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.delete("/sessions/{session_id}/delete")
async def delete_file(session_id: str, path: str):
    """
    Delete file or directory in sandbox.
    
    Args:
        session_id: Session ID
        path: File or directory path
        
    Returns:
        Success message
    """
    try:
        sandbox = await sandbox_manager.get_or_create_sandbox(session_id)
        if not sandbox:
            raise HTTPException(
                status_code=404,
                detail=f"No sandbox found for session {session_id}"
            )
        
        # Check if path exists
        qpath = _sh_quote(path)
        check_result = await sandbox.exec_command(f"test -e {qpath} && echo 'exists'")
        if not check_result.success or 'exists' not in check_result.stdout:
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path}"
            )
        
        # Delete file or directory
        result = await sandbox.exec_command(f"rm -rf {qpath}")
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete: {result.stderr}"
            )
        
        logger.info(f"[SandboxFiles] Deleted: {path} for session {session_id}")
        
        return {"status": "success", "path": path}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SandboxFiles] Error deleting: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/sessions/{session_id}/download")
async def download_file(session_id: str, path: str):
    """
    Download file or directory from sandbox.
    
    For files: Returns the file content directly.
    For directories: Returns a zip archive of the directory.
    
    Args:
        session_id: Session ID
        path: File or directory path
        
    Returns:
        File content or zip archive as streaming response
    """
    try:
        import unicodedata
        from urllib.parse import quote

        # Build a Content-Disposition header value that is safe for Starlette (latin-1 headers)
        # while still supporting unicode filenames via RFC 5987 (filename*=UTF-8'')
        def _content_disposition_attachment(original_name: str) -> str:
            # ASCII fallback (remove non-ascii)
            ascii_name = (
                unicodedata.normalize("NFKD", original_name)
                .encode("ascii", "ignore")
                .decode("ascii")
            ).strip()
            ascii_name = ascii_name.replace('"', "").replace("\\", "")
            if not ascii_name:
                ascii_name = "download"

            # Percent-encode UTF-8 filename for filename*
            encoded = quote(original_name, safe="")
            return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"

        sandbox = await _get_existing_sandbox(session_id)
        qpath = _sh_quote(path)
        
        # Check if path exists and get type
        check_result = await sandbox.exec_command(
            f"if test -d {qpath}; then echo 'directory'; elif test -f {qpath}; then echo 'file'; else echo 'notfound'; fi"
        )
        path_type = check_result.stdout.strip()
        
        if path_type == 'notfound':
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path}"
            )
        
        # Get filename for Content-Disposition
        filename = path.rstrip('/').split('/')[-1]
        
        if path_type == 'file':
            # Download single file
            result = await sandbox.exec_command(f"base64 {qpath}")
            if not result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read file: {result.stderr}"
                )
            
            file_content = base64.b64decode(result.stdout.strip())
            
            # Determine media type
            extension = filename.split('.')[-1].lower() if '.' in filename else ''
            media_types = {
                'txt': 'text/plain',
                'py': 'text/x-python',
                'js': 'text/javascript',
                'ts': 'text/typescript',
                'json': 'application/json',
                'html': 'text/html',
                'css': 'text/css',
                'csv': 'text/csv',
                'md': 'text/markdown',
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'svg': 'image/svg+xml',
                'pdf': 'application/pdf',
                'zip': 'application/zip',
            }
            media_type = media_types.get(extension, 'application/octet-stream')
            
            logger.info(f"[SandboxFiles] Downloading file: {path} for session {session_id}")
            
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=media_type,
                headers={
                    "Content-Disposition": _content_disposition_attachment(filename),
                    "Content-Length": str(len(file_content))
                }
            )
        
        else:
            # Download directory as zip
            # Create zip in memory
            zip_buffer = io.BytesIO()
            
            # Get all files in directory recursively
            find_result = await sandbox.exec_command(
                f"find {qpath} -type f -printf '%P\\0' 2>/dev/null"
            )
            
            if not find_result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to list directory: {find_result.stderr}"
                )
            
            files = [f for f in find_result.stdout.split('\0') if f]
            base_dir = path.rstrip("/") or "/"
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for relative_path in files:
                    full_path = _join_path(base_dir, relative_path)
                    
                    # Read file content as base64
                    result = await sandbox.exec_command(f"base64 {_sh_quote(full_path)}")
                    if result.success:
                        try:
                            file_content = base64.b64decode(result.stdout.strip())
                            # Add to zip with relative path
                            zf.writestr(relative_path, file_content)
                        except Exception as e:
                            logger.warning(f"[SandboxFiles] Skipping file {relative_path}: {e}")
                            continue
            
            zip_buffer.seek(0)
            zip_filename = f"{filename}.zip"
            
            logger.info(f"[SandboxFiles] Downloading directory as zip: {path} for session {session_id}")
            
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": _content_disposition_attachment(zip_filename)
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[SandboxFiles] Error downloading: {e}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )
