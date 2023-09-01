import httpx
from dotenv import load_dotenv
import os

load_dotenv()


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "User-Agent": "GitHub-PR-Bot",
    "Accept": "application/vnd.github.v3+json",
}


async def get_pr_files(owner, repo, pr_number):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=HEADERS)
        return response.json()


async def get_pr_diff(owner, repo, pr_number):
    url = f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{pr_number}.diff"

    async with httpx.AsyncClient() as client:
        diff_response = await client.get(url, headers=HEADERS)
        return diff_response.text


async def post_pr_comment(owner, repo, pr_number, comment_body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    data = {"body": comment_body}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=HEADERS)
        return response.json()
