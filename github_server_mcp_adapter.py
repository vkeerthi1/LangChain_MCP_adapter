import os
import requests
from fastmcp import FastMCP
from dotenv import load_dotenv
import asyncio
# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GH_OWNER", "")
REPO = os.getenv("GH_REPO", "")
BASE_URL = "https://github.boschdevcloud.com/api/v3"

if not GITHUB_TOKEN:
    raise ValueError("Missing GITHUB_TOKEN environment variable")


# ----------------------------
# MCP Server Metadata (Required!)
# ----------------------------
mcp = FastMCP()


# ==========================================================
# Resources
# ==========================================================

@mcp.resource("github://prs/recent")
def recent_pull_requests():
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {"state": "open", "per_page": 10}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return [
        {
            "number": p["number"],
            "title": p["title"],
            "author": p["user"]["login"],
            "url": p["html_url"],
            "branch": p["head"]["ref"]
        }
        for p in resp.json()
    ]


@mcp.resource("github://issues/recent")
def recent_issues():
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {"state": "open", "per_page": 100}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    issues = resp.json()
    return [
        #{"number": i["number"], "title": i["title"], "url": i["html_url"], "state": i["state"]}
        #for i in issues
        #if not i.get("pull_request")
        issues
    ]


# ==========================================================
# Tools
# ==========================================================

@mcp.tool()
def get_pr_details(number: int):
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls/{number}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def comment_on_pr(number: int, message: str):
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/issues/{number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.post(url, headers=headers, json={"body": message}, timeout=15)
    resp.raise_for_status()
    return {"status": "comment_added", "url": resp.json().get("html_url")}


@mcp.tool()
def list_all_issues(state: str = "open", per_page: int = 100):
    """List all issues including those that might be PRs. State can be 'open', 'closed', or 'all'."""
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/issues"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {"state": state, "per_page": per_page}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return [
        {
            "number": i["number"],
            "title": i["title"],
            "url": i["html_url"],
            "state": i["state"],
            "is_pull_request": "pull_request" in i,
            "user": i["user"]["login"]
        }
        for i in resp.json()
    ]

@mcp.tool()
def get_pr_review_comments(number: int):
    """Get review comments for a specific pull request"""
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls/{number}/comments"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    comments = resp.json()
    return [
        {
            "user": c["user"]["login"],
            "body": c["body"],
            "path": c.get("path", ""),
            "line": c.get("line"),
            "created_at": c["created_at"]
        }
        for c in comments
    ]


@mcp.tool()
def get_pr_reviews(number: int):
    """Get review summaries (approve/request changes/comment) for a pull request"""
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/pulls/{number}/reviews"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    reviews = resp.json()
    return [
        {
            "user": r["user"]["login"],
            "state": r["state"],  # APPROVED, CHANGES_REQUESTED, COMMENTED
            "body": r.get("body", ""),
            "submitted_at": r["submitted_at"]
        }
        for r in reviews
    ]
# ==========================================================
# Prompt (Optional)
# ==========================================================

@mcp.prompt("github_helper")
def github_prompt():
    return """
- Use resources first to gather information.
- Use tools only when the user requests an action.
"""


# ==========================================================
# Run MCP Server (FINAL FIX)
# ==========================================================

if __name__ == "__main__":
    #mcp.run(transport="http", host="127.0.0.1", port=8089, path="/mcp")
    #LangChain MCP adapters support ONLY the streamable HTTP mode.
    asyncio.run(
        mcp.run_streamable_http_async(
            host="127.0.0.1",
            port=8089,
            path="/mcp"
        )
    )


