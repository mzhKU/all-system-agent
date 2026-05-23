import os
import sys
import docker
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smolagents import CodeAgent
from tests.mock_engine import MockEngine

from main.tools.container import \
    ContainerStatus,  \
    StartContainer,   \
    CreateVolume,     \
    InstallUtilities, \
    RemoveContainer
    
from main.tools.repository import \
    CloneRepository, \
    CheckoutBranch,  \
    EditCode,        \
    ReadCode,        \
    ListCode,        \
    GitStatus,       \
    GitCommit,       \
    PushBranch,      \
    OpenMergeRequest,\
    CreateFile,      \
    Comment

def generate_dummy_java_file():
    dummy_random_string = str(random.randint(0, 100))
    content  = ""
    content += "package ch.mzh.avclient.domain;\n"
    content += f"// Random String: {dummy_random_string}\n"
    content += "public enum OutputSize {\n"
    content += "    COMPACT, FULL\n"
    content += "}"
    return content

def generate_dummy_commit_message():
    dummy_random_string = str(random.randint(0, 100))
    return f"Commit: {dummy_random_string}"

if __name__ == "__main__":
    gitlab_token = "glpat-afRR9teu-luAe5JxqKY-2G86MQp1OjgH.01.0w1kmzta8"
    gitlab_host = "100.122.48.109"
    gitlab_port = 8081
    gitlab_repo = "mzhku/all-system-development.git"
    project_id = 1
    default_title = "Default Merge Request Title"
    issue_iid = 1
    mr_url = "abc"

    dummy_namespace_project = "mzhku/all-system-development.git"
    dummy_user_comment = "Write a domain class to model a stock exchange."
    dummy_edit_file_path = "avclient/src/main/java/ch/mzh/avclient/domain/OutputSize.java"
    dummy_create_file_path = "avclient/src/main/java/ch/mzh/avclient/domain/NewFile.java"
    dummy_edited_java_file_content = generate_dummy_java_file()
    dummy_create_file_content = generate_dummy_java_file()
    dummy_commit_message = generate_dummy_commit_message()
    dummy_source_branch = "dummy_branch"
    dummy_target_branch = "main"
    dummy_merge_request_title = "Merge request"
    dummy_comment = "The work is done, please review the merge request."
    
    CREATE_VOLUME = """
        Thought: I will first create a volume.
        ```
        <code>
        volume_mounts = create_volume()
        </code>
        ```
        """
    START_CONTAINER = """
        Thought: I will now start a container.
        ```
        <code>
        container_id = start_container(image="alpine:3.19", volume_mounts_data=volume_mounts)
        </code>
        ```
        """
    CHECK_STATUS = """
        Thought: I will check the status of the container.
        ```
        <code>
        check_container_status(container_id_or_container=container_id)
        </code>
        ```
        """
    INSTALL_UTILITY =  """
        Thought: If the container is running, I can install some utilities in the container.
        One utility I will need is git.
        If the container is not running, I need to check if it is still starting, or if it needs to be started.
        ```
        <code>
        install_status = install_utilities(container_id_or_container=container_id, utility_name="git")
        </code>
        ```
        """
    CLONE_REPOSITORY = f"""
        Thought: Now I'll clone the repository the user is asking about.
        Prior to cloning, I will clear the target directory to prevent any git errors from trying to clone into a non-empty directory.
        I will clone it into the mounted volume such that I can edit it and run code.
        I do this to address the request by the user.
        The np argument is the the namespace and the project in the format <NAMESPACE>/<PROJECT>.
        ```
        <code>
        clone_repository("{dummy_namespace_project}")
        </code>
        ```
        """
    CHECKOUT_BRANCH = f"""
        Thought: I will checkout a dedicated branch for my changes.
        ```
        <code>
        checkout_branch("{dummy_source_branch}")
        </code>
        ```
        """
    GIT_STATUS = """
        Thought: I will check the git status.
        ```
        <code>
        git_status()
        </code>
        ```
    """
    GIT_COMMIT = f"""
        Thought: I will commit the modified files.
        ```
        <code>
        git_commit(["{dummy_edit_file_path}"], "{dummy_commit_message}")
        </code>
        ```
    """
    LIST = """
        Thought: I will list all files in the repository.
        ```
        <code>
        list_directory()
        </code>
        ```
    """
    CREATE = f"""
        Thought: I will create a new file.
        ```
        <code>
        create_file("{dummy_create_file_path}", \"\"\"{dummy_create_file_content}\"\"\")
        </code>
        ```
    """
    EDIT = f"""
        Thought: I will make edits.
        ```
        <code>
        edit_code("{dummy_edit_file_path}", \"\"\"{dummy_edited_java_file_content}\"\"\")
        </code>
        ```
        """
    READ = f"""
        Thought: I will read a file.
        ```
        <code>
        read_code("{dummy_edit_file_path}")
        </code>
        ```
        """
    COMMIT = """
        Thought: I will commit the changes.
        ```
        <code>
        commit(files)
        </code>
        ```
        """
    PUSH_BRANCH = """
        Thought: I will push the currently checked out branch to the origin.
        ```
        <code>
        git_push()
        </code>
        ```
        """
    OPEN_MERGE_REQUEST = f"""
        Thought: I will open a merge request for the changes of the source branch.
        ```
        <code>
        open_merge_request("{dummy_source_branch}", "{dummy_target_branch}", "{dummy_merge_request_title}")
        </code>
        ```
        """
    POST_COMMENT_TO_WORK_ITEM = f"""
        Thought: I will post a comment to the issue addressing the REVIEWER to take a look at my merge request.
        ```
        <code>
        comment(issue_iid="{issue_iid}", comment_content="{dummy_comment}", recipient_type="REVIEWER")
        </code>
        ```
        """
    REMOVE_CONTAINER = """
        Thought: This is all I need to do, I will remove the container.
        ```
        <code>
        remove_container(container_id_or_container=container_id)
        </code>
        ```
        """
    FINAL_ANSWER = """
        Thought: I can now return the final answer
        ```
        <code>
        final_answer("All done")
        </code>
        ```
        """

    mocked_llm_steps = [
        CREATE_VOLUME,
        START_CONTAINER,
        CHECK_STATUS,
        INSTALL_UTILITY,
        CHECK_STATUS,
        CLONE_REPOSITORY,
        CHECKOUT_BRANCH,
        GIT_STATUS,
        LIST,
        READ,
        CREATE,
        EDIT,
        GIT_COMMIT,
        GIT_STATUS,
        PUSH_BRANCH,
        OPEN_MERGE_REQUEST,
        POST_COMMENT_TO_WORK_ITEM,
        REMOVE_CONTAINER,
        FINAL_ANSWER
    ]
    
    model = MockEngine(mocked_llm_steps)
    client = docker.from_env()

    local_repository_path = str(Path(os.path.abspath("agent-data")).resolve())
    
    agent = CodeAgent(
        tools = [
            StartContainer(client),
            ContainerStatus(client),
            CreateVolume(
                target="/app/data",
                source=str(Path(os.path.abspath("agent-data")).resolve()),
            ),
            InstallUtilities(client),
            RemoveContainer(client),
            CloneRepository(
                host=f"{gitlab_host}",
                port=f"{gitlab_port}",
                access_token=f"{gitlab_token}",
                local_repository_path=local_repository_path,
                local_repository_path_backup=local_repository_path + "-backup"
            ),
            CheckoutBranch(local_repository_path),
            ListCode(local_repository_path),
            CreateFile(local_repository_path),
            EditCode(local_repository_path),
            ReadCode(local_repository_path),
            GitStatus(local_repository_path),
            GitCommit(local_repository_path),
            PushBranch(
                local_repository_path=local_repository_path,
                access_token="glpat-afRR9teu-luAe5JxqKY-2G86MQp1OjgH.01.0w1kmzta8"
            ),
            OpenMergeRequest(
                gitlab_url=f"http://{gitlab_host}:{gitlab_port}",
                project_id=f"{project_id}",
                access_token=f"{gitlab_token}",
                default_title=f"{default_title}"
            ),
            Comment(
                gitlab_url=f"http://{gitlab_host}:{gitlab_port}",
                project_id=f"{project_id}",
                access_token=f"{gitlab_token}"
            )
        ],
        stream_outputs=False,
        model=model,
        additional_authorized_imports=["pathlib"]
    )

    agent.run("dummy")
    print(agent)
