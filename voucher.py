import requests
import json
from dotenv import load_dotenv
import os
load_dotenv()

def voucher():
    url = os.getenv('api-url-voucher')
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
    response = voucher()
    print(response)