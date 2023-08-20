from pydantic import BaseModel


class PingResponse(BaseModel):
    ping: str
