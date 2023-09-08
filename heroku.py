from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import logging
import sys
import json
import requests

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from main import smoke_test, handle_webhook


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("Docu Mentor")
load_dotenv()


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


@app.get("/")
async def root():
    return await smoke_test()

@app.post("/webhook/")
async def handle_webhook_route(request: Request):
   return await handle_webhook(request)
