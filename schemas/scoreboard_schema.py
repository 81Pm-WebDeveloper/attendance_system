from pydantic import BaseModel

class ScoreRequest(BaseModel):
    username: str
    tries: int

class guessRequest(BaseModel):
    username: str
    guess: str