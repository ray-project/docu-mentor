from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
import os
import openai
import logging
import string
import sys
from ray import serve

from utils import (
    generate_jwt,
    get_installation_access_token,
    get_diff_url,
    files_to_diff_dict
)


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("Doc Sanity")


GREETING = """
👋 Hi, I'm @docu-mentor, an LLM-powered GitHub app
powered by [Anyscale Endpoints](https://app.endpoints.anyscale.com/)
that gives you actionable feedback on your writing.

Simply create a new comment in this PR that says:

@docu-mentor run

and I will start my analysis. I only look at what you changed
in this PR. If you only want me to look at specific files or folders,
you can specify them like this:

@docu-mentor run doc/ README.md

In this example, I'll have a look at all files contained in the "doc/"
folder and the file "README.md". All good? Let's get started!
"""

load_dotenv()

# If the app was installed, retrieve the installation access token through the App's
# private key and app ID, by generating an intermediary JWT token.
APP_ID = os.environ.get("APP_ID")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY", "")

ANYSCALE_API_ENDPOINT = "https://api.endpoints.anyscale.com/v1"
openai.api_base = ANYSCALE_API_ENDPOINT
openai.api_key = os.environ.get("ANYSCALE_API_KEY")


SYSTEM_CONTENT = """
You are a helpful assistant.
Improve the following <content>. Criticise syntax, grammar, punctuation, style, etc.
Recommend common technical writing knowledge, such as used in Vale
and the Google developer documentation style guide.
If the content is good, don't comment on it.
Do not comment on file names, just the actual text.
The <content> will be in JSON format and contains file name keys and text values.
You can use GitHub-flavored markdown syntax.
Make sure to give very concise feedback per file.
"""

def sanitize(
        content,
        model="meta-llama/Llama-2-70b-chat-hf",
        system_content=SYSTEM_CONTENT,
        extra_instructions="Improve this content."
    ):
    """The content can be any string in principle, but the system prompt is
    crafted for dictionary data of the form {'file_name': 'file_content'}.
    """
    return openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"This is the content: {content}. {extra_instructions}"},
        ],
        temperature=0.7,
    )


app = FastAPI()

@serve.deployment(route_prefix="/")
@serve.ingress(app)
class ServeBot:
    @app.get("/")
    async def root(self):
        return {"message": "Doc Sanity reporting for duty!"}

    @app.post("/webhook/")
    async def handle_github_webhook(self, request: Request):
        data = await request.json()

        installation = data.get("installation")
        if installation and installation.get("id"):
            installation_id = installation.get("id")
            logger.info(f"Installation ID: {installation_id}")

            JWT_TOKEN = generate_jwt()

            installation_access_token = await get_installation_access_token(
                JWT_TOKEN, installation_id
            )

            headers = {
                "Authorization": f"token {installation_access_token}",
                "User-Agent": "Your-App-Name",
                "Accept": "application/vnd.github.VERSION.diff",
            }
        else:
            raise ValueError("No app installation found.")

        # If PR exists and is opened
        if "pull_request" in data.keys() and (
            data["action"] in ["opened"]
        ):  # use "synchronize" for tracking new commits
            pr = data.get("pull_request")

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{pr['issue_url']}/comments",
                    json={"body": GREETING},
                    headers=headers,
                )

            return JSONResponse(content={}, status_code=200)

        # Check if the event is a new or modified issue comment
        if "issue" in data.keys() and data.get("action") in ["created", "edited"]:
            issue = data["issue"]

            # Check if the issue is a pull request
            if "/pull/" in issue["html_url"]:
                pr = issue.get("pull_request")

                # Get the comment body
                comment = data.get("comment")
                comment_body = comment.get("body")
                # Remove all whitespace characters except for regular spaces
                comment_body = comment_body.translate(
                    str.maketrans("", "", string.whitespace.replace(" ", ""))
                )

                # Skip if the bot talks about itself
                author_handle = comment["user"]["login"]

                # Check if the bot is mentioned in the comment
                if (
                    author_handle != "docu-mentor[bot]"
                    and "@docu-mentor run" in comment_body
                ):
                    async with httpx.AsyncClient() as client:
                        # Fetch diff from GitHub
                        files_to_keep = comment_body.replace(
                            "@docu-mentor run", ""
                        ).split(" ")
                        files_to_keep = [item for item in files_to_keep if item]

                        logger.info(files_to_keep)

                        url = get_diff_url(pr)
                        diff_response = await client.get(url, headers=headers)
                        diff = diff_response.text

                        files_with_diff = files_to_diff_dict(diff)

                        # Filter the dictionary
                        if files_to_keep:
                            files_with_diff = {
                                k: files_with_diff[k]
                                for k in files_with_diff
                                if any(sub in k for sub in files_to_keep)
                            }

                        logger.info(files_with_diff.keys())

                        # Sanitize the content
                        chat_completion = sanitize(files_with_diff)

                        logger.info(chat_completion)
                        model = chat_completion.get("model")
                        usage = chat_completion.get("usage")
                        prompt_tokens = usage.get("prompt_tokens")
                        completion_tokens = usage.get("completion_tokens")
                        content = chat_completion["choices"][0]["message"]["content"]

                        # Let's comment on the PR
                        await client.post(
                            f"{comment['issue_url']}/comments",
                            json={
                                "body": f":rocket: Doc Sanity finished analysing your PR! :rocket:\n\n"
                                + "Take a look at your results:\n"
                                + f"{content}\n\n"
                                + "This bot is proudly powered by [Anyscale Endpoints](https://app.endpoints.anyscale.com/).\n"
                                + f"It used the model {model}, used {prompt_tokens} prompt tokens, "
                                + f"and {completion_tokens} completion tokens in total."
                            },
                            headers=headers,
                        )


# Run with: serve run main:bot
bot = ServeBot.bind()
