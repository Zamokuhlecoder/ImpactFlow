from typing import Literal

from pydantic import BaseModel


class LiveHealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyHealthResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["connected"] = "connected"
