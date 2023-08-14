from typing import Annotated, List, Union

from fastapi import APIRouter, File, UploadFile, Request, Header, HTTPException
from pydantic import BaseModel

from app.utils.utils import save_audio_file, transcribeFile

router = APIRouter()


class Transcription(BaseModel):
    text: str
    filename: str


@router.post("/", response_model=Transcription)
async def post_audio(
    request: Request,
    file: UploadFile = File(...),
    Authentication: Annotated[Union[str, None], Header()] = None,
):
    print(f"Authorization header: {Authentication}")

    try:
        """Receive audio file and save it to disk. and then transcribe the audio file"""
        file_path = save_audio_file(file)
        data = transcribeFile(file_path)
        return Transcription(filename=file.filename, text=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=e.__str__())
