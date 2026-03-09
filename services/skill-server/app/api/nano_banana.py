from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.schemas.nano_banana import NanoBananaResponse


router = APIRouter(prefix="/v1/nano-banana", tags=["nano-banana"])


@router.post("/generate", response_model=NanoBananaResponse)
def generate(
    request: Request,
    prompt: Annotated[str, Form()],
    resolution: Annotated[str, Form()] = "1K",
    filename_hint: Annotated[str | None, Form()] = None,
    files: list[UploadFile] | None = File(default=None),
) -> NanoBananaResponse:
    service = request.app.state.nano_banana_service
    settings = request.app.state.settings
    input_files: list[dict[str, object]] = []

    for upload in files or []:
        data = upload.file.read()
        if len(data) > settings.max_upload_bytes:
            raise RuntimeError(
                f"Upload {upload.filename or 'file'} exceeds {settings.max_upload_bytes} bytes."
            )
        input_files.append(
            {
                "filename": upload.filename or "upload.bin",
                "content_type": upload.content_type or "application/octet-stream",
                "data": data,
            }
        )

    result = service.generate(
        prompt=prompt,
        resolution=resolution,
        filename_hint=filename_hint,
        input_files=input_files,
        request_id=request.state.request_id,
    )
    return NanoBananaResponse(**result)
