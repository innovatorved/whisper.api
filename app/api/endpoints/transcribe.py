from fastapi import APIRouter, File, UploadFile, Request, Header
from pydantic import BaseModel

router = APIRouter()


class AudioFile(BaseModel):
    filename: str
    content_type: str


@router.post("/")
async def post_audio(
    request: Request, file: UploadFile = File(...), Authorization: str = Header(...)
):
    """Receive audio file and save it to disk."""
    print(f"Authorization header: {Authorization}")

    with open(file.filename, "wb") as f:
        f.write(file.file.read())

    return AudioFile(filename=file.filename, content_type=file.content_type)
