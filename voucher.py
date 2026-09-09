import requests
import json
from dotenv import load_dotenv
import os
from config.features import VOUCHERS_ENABLED
load_dotenv()

def voucher():
    if not VOUCHERS_ENABLED:
        return {"disabled": True, "message": "Voucher flow is disabled"}
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
