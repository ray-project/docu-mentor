from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
import os
import openai
import logging
import sys
import time
import jwt


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("Doc Sanity")

load_dotenv()

greeting = "👋 Hi, I'm @doc-sanity, an LLM-powered GitHub app that gives you actionable feedback on the writing contained in your pull requests."

openai.api_base = "https://api.endpoints.anyscale.com/v1"
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = FastAPI()

# By default, use a personal access token.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


# If the app was installed, retrieve the installation access token through the App's
# private key and app ID, by generating an intermediary JWT token.
APP_ID = os.environ.get("APP_ID")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")


def generate_jwt():
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + (10 * 60),
        "iss": APP_ID,
    }
    jwt_token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    return jwt_token


@app.get("/")
async def root():
    return {"message": "Doc Sanity reporting for duty!"}


async def get_installation_access_token(jwt, installation_id):
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Accept": "application/vnd.github.v3+json",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        return response.json()["token"]


def get_diff_url(pr):
    """GitHub 302s to this URL."""
    original_url = pr.get("url")
    parts = original_url.split("/")
    owner, repo, pr_number = parts[-4], parts[-3], parts[-1]
    return f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{pr_number}.diff"


def files_to_diff_dict(diff):
    files_with_diff = {}
    current_file = None
    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            current_file = line.split(' ')[2][2:]
            files_with_diff[current_file] = {'text': []}
        elif line.startswith('+') and not line.startswith('+++'):
            files_with_diff[current_file]['text'].append(line[1:])
    return files_with_diff


@app.post("/webhook/")
async def handle_github_webhook(request: Request):
    data = await request.json()
    pr = data.get("pull_request")

    logger.info(data)

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "User-Agent": "GitHub-PR-Bot",
        "Accept": "application/vnd.github.v3+json"
    }

    installation = data.get("installation")
    if installation and installation.get("id"):
        installation_id = installation.get("id")
        logger.info(f"Installation ID: {installation_id}")

        JWT_TOKEN = generate_jwt()

        installation_access_token = await get_installation_access_token(
            JWT_TOKEN, 
            installation_id
        )
    
        headers = {
            'Authorization': f'token {installation_access_token}',
            'User-Agent': 'Your-App-Name',
            'Accept': 'application/vnd.github.VERSION.diff'
        }    
    
    # Check if the event is a issue comment
    issue = data["issue"]
    if issue and data.get("action") in ["created", "edited"]:

        # Check if the issue is a pull request
        if "/pull/" in issue["html_url"]:
            
            # Get the comment body
            comment = data.get("comment")
            comment_body = comment.get("body")

            # Check if the bot is mentioned in the comment
            if "@doc-sanity" in comment_body:
                # The bot is mentioned in the PR comment
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{pr['issue_url']}/comments",
                        json={
                            "body": f"I react to @mentions!"
                        },
                        headers=headers
                    )
    
    # Ensure PR exists and is opened or synchronized
    if pr and (data["action"] in ["opened", "synchronize"]):
        async with httpx.AsyncClient() as client:
            # Fetch diff from GitHub

            url = get_diff_url(pr)
            diff_response = await client.get(url, headers=headers)
            diff = diff_response.text
            logger.info("Raw diff with meta-data:" + diff)

            files_with_diff = files_to_diff_dict(diff)
            logger.info(files_with_diff)

            chat_completion = openai.ChatCompletion.create(
                model="meta-llama/Llama-2-70b-chat-hf",
                messages=[
                    {"role": "system", 
                     "content": "You are a helpful assistant." +
                     "Improve the following <content>. Criticise grammar, punctuation, style etc." +
                     "Make it so that you recommend common technical writing knowledge " +
                     "The <content> will be in JSON format and contain file names and 'text'. " +
                     "You can use GitHub-flavored markdown syntax. " +
                     "Make sure to give very concise feedback per file."}, 
                    {"role": "user", 
                     "content": f"This is the content: {files_with_diff}"}
                ],
                temperature=0.7
            )

            logger.info(chat_completion)
            model = chat_completion.get("model")
            usage = chat_completion.get("usage")
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            content = chat_completion["choices"][0]["message"]["content"]
                        
            # Let's comment on the PR
            await client.post(
                f"{pr['issue_url']}/comments",
                json={
                    "body": f":rocket: Doc Sanity finished analysing your PR! :rocket:\n\n" +
                    "Take a look at your results:\n" +
                    f"{content}\n\n" +
                    "This bot is proudly powered by [Anyscale Endpoints](https://app.endpoints.anyscale.com/).\n" +
                    f"It used the model {model}, used {prompt_tokens} prompt tokens, and {completion_tokens} completion tokens in total."
                },
                headers=headers
            )
    
    return JSONResponse(content={}, status_code=200)
