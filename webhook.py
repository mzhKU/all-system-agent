from flask import Flask, request, jsonify
import gitlab
from dotenv import load_dotenv
import os

from codebase_context import RemoteCodebaseReader
from smolagents import OpenAIServerModel, CodeAgent

load_dotenv()


app = Flask(__name__)

QWEN = "qwen3.5:latest"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "dummy"

GITLAB_URL = "http://localhost:8081"
API_URL = "/api/v4/projects"
TOKEN = os.getenv("TOKEN") # Expires 06.06.2026
PROJECT_ID = "1"
SOURCE_BRANCH = "dev"
TARGET_BRANCH = "main"

def create_pull_request(title):
    try:
        gl = gitlab.Gitlab(GITLAB_URL, private_token=TOKEN)
        project = gl.projects.get(PROJECT_ID)
        mr = project.mergerequests.create({
            'source_branch': SOURCE_BRANCH,
            'target_branch': TARGET_BRANCH,
            'title': title,
        })
        print(f"✅ Merge Request created: {mr.iid}, {mr.web_url}")
    except gitlab.exceptions.GitlabAuthenticationError:
        print("❌ Authentication failed. Check your token and permissions.")
    except gitlab.exceptions.GitlabCreateError as e:
        print(f"❌ Failed to create MR: {e.error_message}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-Gitlab-Event", "Unknown")
    payload = request.json
    if event_type == "Note Hook":
        comment = payload['object_attributes']['description']
        author_id = str(payload['object_attributes']['author_id'])
        print("FROM AUTHOR ID [" + author_id + "]: " + comment)
        if "@AGENT" in comment:
            model = OpenAIServerModel(model_id=QWEN, api_base=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
            agent = CodeAgent(
                tools=[
                    RemoteCodebaseReader(
                        gitlab_url="http://localhost:8081",
                        access_token=TOKEN,
                        repo_name="mzhku/all-system-development",
                        max_tokens=200_000,
                        file_extension_filter=".java"
                    )
                ], 
                model=model,
                add_base_tools=True,
                additional_authorized_imports=["codebase_context", "os"],
                instructions="You are not allowed to use internal knowledge for facts. Every factual statement must come from a tool call."
                )
            # create_pull_request("Dummy")
            agent.run(comment)
    else:
        print(f"📦 Received event: {event_type}")
    return jsonify({"status": "OK"}), 200 # CHECK THIS

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
