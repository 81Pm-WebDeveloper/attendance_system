from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.scoreboard import Score
from schemas.scoreboard_schema import ScoreRequest
from datetime import datetime, date

def submit_score(db: Session, data: ScoreRequest):
    player = db.query(Score).filter(Score.username == data.username).first()

    if not player:
        player = Score(username=data.username, score=0, last_submission=None)
        db.add(player)
        db.commit()

    if player.last_submission and player.last_submission.date() == date.today():
        return {"message": "Score already submitted today", "points": 0}

    score_map = {1: 5, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}
    points = score_map.get(data.tries, 0)
    player.score += points
    player.last_submission = date.today()

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