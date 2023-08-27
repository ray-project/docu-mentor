from fastapi import FastAPI, Request
import httpx
from dotenv import load_dotenv
import os

load_dotenv()


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/webhook/")
async def handle_github_webhook(request: Request):
    data = await request.json()
    pr = data.get("pull_request")
    
    # Ensure PR exists and is opened or synchronized
    if pr and (data["action"] in ["opened", "synchronized"]):
        async with httpx.AsyncClient() as client:
            # Fetch diff from GitHub
            resp = await client.get(pr["diff_url"], headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "User-Agent": "GitHub-Diff-Bot"
            })
            
            diff = resp.text
            
            # Analyze the diff (this is a simplistic check)
            if "TODO" in diff:
                # Found a TODO in the PR, let's comment on the PR
                await client.post(
                    f"{pr['issue_url']}/comments",
                    json={"body": "Found a TODO in your PR!"},
                    headers={
                        "Authorization": f"token {GITHUB_TOKEN}",
                        "User-Agent": "GitHub-Diff-Bot"
                    }
                )
    
    return {"status": "success"}