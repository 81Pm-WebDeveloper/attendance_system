from fastapi import HTTPException,status
from sqlalchemy.orm import Session
from models.scoreboard import Score
from schemas.scoreboard_schema import ScoreRequest,guessRequest
from datetime import datetime, date
import json
import pytz

philippines = pytz.timezone("Asia/Manila")
today_ = datetime.now(philippines).date()

def save_guesses(db:Session, data: guessRequest):
    score = db.query(Score).filter(Score.username == data.username).first()

    if not score:
        guesses = [data.guess]
        db.add(Score(
            username=data.username,
            score=0,
            guesses=json.dumps(guesses),
            last_guess_submission=today_
        ))
    else:
        if score.last_guess_submission == today_:
            current = json.loads(score.guesses or "[]")
            if data.guess in current:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Word already submitted"
                )
            current.append(data.guess)
            score.guesses = json.dumps(current)
        else:
            score.guesses = json.dumps([data.guess])
            score.last_guess_submission = today_
    db.commit()
    return {"message": "Guess Submitted"}

def fetch_guesses(db: Session, username: str):
    guesses = db.query(Score.guesses, Score.last_guess_submission).filter(Score.username == username).first()
    
    if guesses and guesses[1] == today_:
        return json.loads(guesses[0])
    return []


def submit_score(db: Session, data: ScoreRequest):
    player = db.query(Score).filter(Score.username == data.username).first()

    if not player:
        player = Score(username=data.username, score=0, last_submission=None)
        db.add(player)
        db.commit()

    if player.last_submission and player.last_submission == today_:
        return {"message": "Score already submitted today", "points": 0}

    score_map = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}
    points = score_map.get(data.tries, 0)
    player.score += points
    player.last_submission = today_

    db.commit()
    return {"message": "Score Submitted", "points": points}

def get_leaderboard(db:Session):
    leaderboard = db.query(Score).order_by(Score.score.desc()).all()

    response = [
        {
            'username': row.username,
            'score': row.score
        }
        for row in leaderboard
    ]
    return response