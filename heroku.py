from dotenv import load_dotenv
import json
import os
import requests

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


load_dotenv()

ANYSCALE_TOKEN = os.environ.get("ANYSCALE_TOKEN")
ANYSCALE_SERVICE_URL = os.environ.get("BASE_URL")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Restrict this to the domains you want to allow
    # access to your service.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query")
async def handle_query(request: Request):
    data = await request.json()
    headers = {"Authorization": f"Bearer {ANYSCALE_TOKEN}"}

    res = requests.post(f"{ANYSCALE_SERVICE_URL}/webhook/", headers=headers, json=data)
    content = json.loads(res.content)

    return JSONResponse(content=content, status_code=200)
