import docker
import os
import sys

from pathlib    import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask      import Flask, request, jsonify
from dotenv     import load_dotenv
from smolagents import CodeAgent, OpenAIServerModel


from main.tools.container import \
    StartContainer,   \
    ContainerStatus,  \
    CreateVolume,     \
    InstallUtilities, \
    RemoveContainer

from main.tools.repository import \
    CloneRepository, \
    CheckoutBranch,  \
    EditCode,        \
    ListCode,        \
    GitStatus,       \
    ReadCode,        \
    ListCode,        \
    GitCommit,       \
    PushBranch,      \
    OpenMergeRequest,\
    CreateFile,      \
    Comment

load_dotenv()


app = Flask(__name__)

QWEN = "qwen3.5:latest"
GEMMA = "gemma4:latest"

OLLAMA_BASE_URL = "http://100.122.48.109:11434/v1"
OLLAMA_API_KEY = "dummy"

DOCKER_IMAGE_PYTHON = "alpine:latest"
DOCKER_IMAGE_MAVEN = "maven:3.9.8-eclipse-temurin-21"
DOCKER_IMAGE_ALPINE = "alpine:3.19"

GITLAB_HOST = "100.122.48.109"
GITLAB_PORT = 8081
GITLAB_REPO = "mzhku/all-system-development.git"
GITLAB_TOKEN = "glpat-afRR9teu-luAe5JxqKY-2G86MQp1OjgH.01.0w1kmzta8"

REPO_NAME = "mzhku/all-system-development"
API_URL = "/api/v4/projects"
TOKEN = os.getenv("TOKEN") # Expires 06.06.2026
PROJECT_ID = "1"
SOURCE_BRANCH = "dev"
TARGET_BRANCH = "main"

CODE_AGENT_INSTRUCTIONS = "You are not allowed to use internal knowledge for facts. Every factual statement must come from a tool call."

def create_code_agent(model: OpenAIServerModel, user_comment: str, token: str):
    client = docker.from_env()
    
    if client is None:
        return False

    local_repository_path = str(Path(os.path.abspath("agent-data")).resolve()) # Absolute path on the host
    volume_target = "/app/data"  # Path inside the container

    return CodeAgent(
        tools=[
            StartContainer(client),
            ContainerStatus(client),
            CreateVolume(
                target=volume_target,
                source=local_repository_path,
            ),
            # InstallUtilities(client),
            RemoveContainer(client),
            CloneRepository(
                host=GITLAB_HOST,
                port=GITLAB_PORT,
                access_token=token,
                local_repository_path=local_repository_path,
                local_repository_path_backup=local_repository_path + "-backup"
            ),
            CheckoutBranch(local_repository_path),
            ListCode(local_repository_path),
            EditCode(local_repository_path),
            CreateFile(local_repository_path),
            ReadCode(local_repository_path),
            GitStatus(local_repository_path),
            GitCommit(local_repository_path),
            PushBranch(
                local_repository_path=local_repository_path,
                access_token="glpat-afRR9teu-luAe5JxqKY-2G86MQp1OjgH.01.0w1kmzta8"
            ),
            OpenMergeRequest(
                gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
                project_id=f"{PROJECT_ID}",
                access_token=f"{GITLAB_TOKEN}",
                default_title="Default Merge Request Title"
            ),
            Comment(
                gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
                project_id=f"{PROJECT_ID}",
                access_token=f"{GITLAB_TOKEN}"
            )
        ],
        stream_outputs=False,
        model=model,
        add_base_tools=False,
        instructions=CODE_AGENT_INSTRUCTIONS
    )

def something():
    print("Here")

@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-Gitlab-Event", "Unknown")
    payload = request.json
    if event_type == "Note Hook":    

        repository_url_with_token = f"http://oauth2:{GITLAB_TOKEN}@{GITLAB_HOST}:{GITLAB_PORT}/{payload['project']['path_with_namespace']}"
        user_comment = payload['object_attributes']['description']
        user_id      = str(payload['object_attributes']['author_id'])
        noteable_id = payload['object_attributes']['noteable_id'] # Work item id

        if user_comment.startswith("@AGENT_DEV"):
            user_target = "DEVELOPER"
        elif user_comment.startswith("@AGENT_REV"):
            user_target = "REVIEWER"
        elif user_comment.startswith("@HUMAN"):
            user_target = "HUMAN"
        else:
            user_target = "ANYONE"
        
        # TODO: There should be a first repository load to identify the programming language for the agent to know what container image it should start (Python, Java, ...)
        # TODO: The token should somehow be handled by the agent in memory for not to be leaked to the prompt, maybe by some sort of authentication tool.

        agent_dev_prompt = f"""
        You're a developer agent.
        The message of the work item was written by user with ID {user_id}.
        The message is targeted at a {user_target}.
        The user wrote this comment on the repository work item: {user_comment}.
        The host of the remote repository is {GITLAB_HOST} and the port is {GITLAB_PORT}.
        The namespace and project are {GITLAB_REPO} (provided in the format <NAMESPACE>/<PROJECT>).
        The complete URL of the repository of this work item is: {repository_url_with_token}.
        The work item ID is {noteable_id}, use this ID to formulate the address of where you will send your reply to the comment.
        Remember the work item ID as WORK_ITEM_ID.
        This ID needs to be provided as the argument to the "comment" tool.
        You may use only this repository URL for any git operations, such as cloning or pushing commits.
        To work on the work item, you need to start a dedicated Docker container, a tool to do that is provided.
        You have exactly one Docker image provided to you for spinning up containers. The image is {DOCKER_IMAGE_ALPINE}.
        You will only have to work on Java files, you will not need to work on code of any other language.
        You should confirm the status of the container that you started.
        You will need to mount a volume on the host so you can clone a repository locally to work on the code.
        You will need to edit one or more files, depending on the work item description.
        You will need to checkout a new branch to make your changes.
        You will need to commit your changes.
        You will need to push your changes to the remote repository.
        You will need to open a merge request for your changes.
        You need to leave a comment on the work item describing your changes.
        If you opened a merge request and want to request a review, you should start the comment with "@AGENT_REV".
        If you need more clarification on the work item, you should write a comment to the work item to ask for more clarifications.
        When asking for more clarifications, start the comment with "@HUMAN".
        When you finish your work, you should remove the container that you started and checkout branch "main" again.
        """

        agent_rev_prompt = f"""
        You're a quality assurance and code reviewer agent.
        """

        print("FROM AUTHOR ID [" + user_id + "]: " + user_comment)

        model = OpenAIServerModel(model_id=GEMMA, api_base=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)

        if user_target == "DEVELOPER":
            agent = create_code_agent(model, user_comment, TOKEN)
            agent.run(agent_dev_prompt)

    else:
        print(f"📦 Received event: {event_type}")


    return jsonify({"status": "OK"}), 200 # CHECK THIS

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
