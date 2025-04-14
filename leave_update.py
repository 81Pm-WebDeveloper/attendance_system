import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime, date, timedelta
load_dotenv()

def leave_update(date_1,date_2):
    url = f"{os.getenv('api-url-leave')}?start_date={date_1}&end_date={date_2}"
    headers = {
        "Content-Type" : "application/json",
        "API-KEY": os.getenv('api_key')
    }
    try:
        response = requests.post(url,headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    
if __name__ == "__main__":
    days=5
    today = date.today()
    start_date = today - timedelta(days=days)
    response = leave_update(start_date,today)
    print(response)