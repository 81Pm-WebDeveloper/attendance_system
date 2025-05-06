from pydantic import BaseModel

class ScoreRequest(BaseModel):
    username: str
    tries: int

    