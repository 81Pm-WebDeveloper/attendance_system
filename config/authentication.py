from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from dotenv import load_dotenv
import os

load_dotenv()


API_KEY = os.getenv("api_key")
API_KEY_NAME = "API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def verify_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail ="Invalid API")
    return api_key