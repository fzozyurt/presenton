from http.client import HTTPException
import os
from typing import Annotated, List, Optional
from fastapi import APIRouter, Body, File, Query, UploadFile
from fastapi.responses import PlainTextResponse

from constants.documents import UPLOAD_ACCEPTED_FILE_TYPES
from models.decomposed_file_info import DecomposedFileInfo
from services.temp_file_service import TEMP_FILE_SERVICE
from services.documents_loader import DocumentsLoader
import uuid
from utils.validators import validate_files

FILES_ROUTER = APIRouter(prefix="/files", tags=["Files"])


@FILES_ROUTER.post("/upload", response_model=List[str])
async def upload_files(files: Optional[List[UploadFile]]):
    if not files:
        raise HTTPException(400, "Documents are required")

    temp_dir = TEMP_FILE_SERVICE.create_temp_dir(str(uuid.uuid4()))

    validate_files(files, True, True, 100, UPLOAD_ACCEPTED_FILE_TYPES)

    temp_files: List[str] = []
    if files:
        for each_file in files:
            temp_path = TEMP_FILE_SERVICE.create_temp_file_path(
                each_file.filename, temp_dir
            )
            with open(temp_path, "wb") as f:
                content = await each_file.read()
                f.write(content)

            temp_files.append(temp_path)

    return temp_files


@FILES_ROUTER.post("/decompose", response_model=List[DecomposedFileInfo])
async def decompose_files(
    file_paths: Annotated[List[str], Body(embed=True)],
    language: Annotated[Optional[str], Body()] = None,
):
    temp_dir = TEMP_FILE_SERVICE.create_temp_dir(str(uuid.uuid4()))

    txt_files = []
    other_files = []
    for file_path in file_paths:
        if file_path.endswith(".txt"):
            txt_files.append(file_path)
        else:
            other_files.append(file_path)

    documents_loader = DocumentsLoader(file_paths=other_files, presentation_language=language)
    await documents_loader.load_documents(temp_dir)
    parsed_documents = documents_loader.documents

    response = []
    for index, parsed_doc in enumerate(parsed_documents):
        file_path = TEMP_FILE_SERVICE.create_temp_file_path(
            f"{uuid.uuid4()}.txt", temp_dir
        )
        parsed_doc = parsed_doc.replace("<br>", "\n")
        with open(file_path, "w", encoding="utf-8") as text_file:
            text_file.write(parsed_doc)
        response.append(
            DecomposedFileInfo(
                name=os.path.basename(other_files[index]), file_path=file_path
            )
        )

    # Return the txt documents as it is
    for each_file in txt_files:
        response.append(
            DecomposedFileInfo(name=os.path.basename(each_file), file_path=each_file)
        )

    return response


@FILES_ROUTER.post("/update")
async def update_files(
    file_path: Annotated[str, Body()],
    file: Annotated[UploadFile, File()],
):
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"message": "File updated successfully"}


@FILES_ROUTER.get("/read", response_class=PlainTextResponse)
async def read_file(path: str = Query(..., description="Absolute path to the file")):
    """Read a temp file's text content. Used by document preview in the browser."""
    import os as _os
    resolved = _os.path.realpath(_os.path.normpath(path))
    allowed_dirs = [
        _os.path.realpath(TEMP_FILE_SERVICE.base_dir),
        _os.path.realpath(_os.environ.get("APP_DATA_DIRECTORY", _os.path.join(_os.path.sep, "tmp", "presenton"))),
    ]
    if not any(resolved.startswith(d) for d in allowed_dirs):
        raise HTTPException(403, "Path not allowed")
    if not _os.path.isfile(resolved):
        raise HTTPException(404, "File not found")
    with open(resolved, "r", encoding="utf-8") as f:
        return f.read()
