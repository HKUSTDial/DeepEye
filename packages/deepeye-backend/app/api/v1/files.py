from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Response
from fastapi.responses import JSONResponse

from app.dependencies import CurrentUserDep, DatabaseDep
from app.models.schemas.file import FileDownload, FileResponse
from app.services.storage_service import StorageService

router = APIRouter(prefix="/files", tags=["files"])
storage_service = StorageService()

@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    db: DatabaseDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
):
    """Upload a file."""
    try:
        return await storage_service.upload_file(
            db=db,
            user_id=current_user.id,
            file=file,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )

@router.get("", response_model=List[FileResponse])
async def list_files(
    db: DatabaseDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
):
    """List user files."""
    return await storage_service.get_files(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

@router.get("/{file_id}", response_model=FileResponse)
async def get_file_metadata(
    file_id: str,
    db: DatabaseDep,
    current_user: CurrentUserDep,
):
    """Get file metadata."""
    file = await storage_service.get_file(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return file

@router.get("/{file_id}/download", response_model=FileDownload)
async def get_download_url(
    file_id: str,
    db: DatabaseDep,
    current_user: CurrentUserDep,
):
    """Get download URL for a file."""
    url = await storage_service.get_download_url(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not generate URL",
        )
    return FileDownload(url=url)

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    db: DatabaseDep,
    current_user: CurrentUserDep,
):
    """Delete a file."""
    success = await storage_service.delete_file(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

