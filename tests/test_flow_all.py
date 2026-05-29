import os
import sys
import docker
import random
from pathlib import Path
from typing import List, Dict, Any

# Ensure necessary paths are included
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Assuming CodeAgent and MockEngine are correctly imported/defined elsewhere
from smolagents import CodeAgent
from tests.mock_engine import MockEngine

# --- 1. Tool Imports and Setup ---

# Developer/Coding Tools
from main.tools.container import \
    ContainerStatus, StartContainer, CreateVolume, InstallUtilities, RemoveContainer
from main.tools.repository import \
    CloneRepository, CheckoutBranch, ListCode, CreateFile, EditCode, ReadCode, \
    GitStatus, GitCommit, PushBranch, \
    OpenMergeRequest, Comment, ApproveOrReject, GitDiff

# --- 2. Helper Functions (Kept for context) ---

def generate_dummy_java_file() -> str:
    """Generates boilerplate Java content for testing."""
    dummy_random_string = str(random.randint(0, 100))
    content  = ""
    content += "package ch.mzh.avclient.domain;\n"
    content += f"// Random String: {dummy_random_string}\n"
    content += "public enum OutputSize {\n"
    content += "    COMPACT, FULL\n"
    content += "}"
    return content

def generate_dummy_commit_message() -> str:
    """Generates a dummy commit message."""
    dummy_random_string = str(random.randint(0, 100))
    return f"Commit: {dummy_random_string}"

# --- 3. Global Variables and Context Setup ---

# Using dummy credentials/paths for structure, assuming real environment setup
GITLAB_TOKEN = "glpat-afRR9teu-luAe5JxqKY-2G86MQp1OjgH.01.0w1kmzta8"
GITLAB_HOST = "100.122.48.109"
GITLAB_PORT = 8081
PROJECT_ID = 1
ISSUE_IID = "1"
MR_IID = "456" # Use specific, consistent IDs for the flow
DEV_SOURCE_BRANCH = "feature/new-domain"
DEV_TARGET_BRANCH = "main"

# Dummy paths and content
dummy_namespace_project = "mzhku/all-system-development.git"
dummy_edit_file_path = "avclient/src/main/java/ch/mzh/avclient/domain/CurrencyModel.java"
dummy_create_file_path = "avclient/src/main/java/ch/mzh/avclient/domain/NewFile.java"
dummy_edited_java_file_content = "" # Will be set dynamically
dummy_create_file_content = ""     # Will be set dynamically
dummy_commit_message = generate_dummy_commit_message()
dummy_comment = "The currency model is missing immutability and validation. The constructor should ensure that the currencyCode is never null and must be validated against ISO standards before assignment. Please fix this."
dummy_fix_commit_message = "fix(currency): Implemented immutability and validation based on review feedback."


# --- 4. Workflow Definitions (The Core Change) ---

def setup_developer_tools(client: docker.DockerClient, local_repo_path: Path):
    """Initializes all tools required by the Developer Agent."""
    return [
        StartContainer(client),
        ContainerStatus(client),
        CreateVolume(
            target="/app/data",
            source=str(local_repo_path),
        ),
        InstallUtilities(client),
        RemoveContainer(client),
        CloneRepository(
            host=f"{GITLAB_HOST}",
            port=f"{GITLAB_PORT}",
            access_token=GITLAB_TOKEN,
            local_repository_path=str(local_repo_path),
            local_repository_path_backup=str(local_repo_path) + "-backup"
        ),
        CheckoutBranch(str(local_repo_path)),
        ListCode(local_repo_path),
        CreateFile(local_repo_path),
        EditCode(local_repo_path),
        ReadCode(local_repo_path),
        GitStatus(local_repo_path),
        GitCommit(local_repo_path),
        PushBranch(
            local_repository_path=str(local_repo_path),
            access_token=GITLAB_TOKEN
        ),
        OpenMergeRequest(
            gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
            project_id=str(PROJECT_ID),
            access_token=GITLAB_TOKEN,
            default_title="Default Merge Request Title"
        ),
        Comment(
            gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
            project_id=str(PROJECT_ID),
            access_token=GITLAB_TOKEN
        ),
        GitDiff(local_repository_path)
    ]


def create_developer_plan(local_repo_path: Path, dummy_edited_java_file_content: str, dummy_create_file_content: str):
    """
    Defines the full sequence of tool calls for the Developer Agent 
    (Initiation -> Work -> Submission).
    """
    print("\n--- 🏗️ PHASE 1 & 2: DEVELOPER WORKFLOW PLAN (INITIAL SUBMISSION) ---")
    
    dev_plan = [
        # Setup Phase
        "SETUP: Create Volume",
        "SETUP: Start Container",
        "SETUP: Install Utilities (git)",
        "SETUP: Clone Repository",
        "SETUP: Checkout Branch",
        
        # Coding Phase (Initial Files)
        "DEV: List Directory (Map Structure)",
        "DEV: Read Code (Understand existing code)",
        "DEV: Create File (Boilerplate)",
        "DEV: Edit Code (Implement initial logic)",
        
        # Commit & Push (Cycle 1 Submission)
        "DEV: Check Status (Pre-commit check)",
        "DEV: Git Commit (Stage and Commit)",
        "DEV: Check Status (Post-commit check)",
        "DEV: Push Branch (Remote Sync)",
        "DEV: Open Merge Request (Create MR)",
        "DEV: Comment (Notify Reviewer)",
        "DEV: Remove Container (Cleanup)",
        "Final Answer"
    ]
    return dev_plan


def create_developer_fix_plan(local_repo_path: Path, dummy_edited_java_file_content: str):
    """
    Defines the full sequence of tool calls for the Developer Agent 
    (Review Feedback Received -> Fix Code -> Resubmit).
    """
    print("\n--- 🛠️ PHASE 4: DEVELOPER FIXING AND RESUBMISSION PLAN ---")
    
    dev_fix_plan = [
        # Setup Phase
        "SETUP: Create Volume",
        "SETUP: Start Container",
        "SETUP: Install Utilities (git)",
        "SETUP: Clone Repository",
        "SETUP: Checkout Branch",

        # Coding Phase (Fixing the Bug)
        "DEV: Edit Code (Overwrite with fixed, immutable code)",
        
        # Commit & Push (Cycle 2 Submission)
        "DEV: Check Status (Pre-commit check)",
        "DEV: Git Commit (Stage and Commit the fix)",
        "DEV: Check Status (Post-commit check)",
        "DEV: Push Branch (Sync the fixed commit)",
        "DEV: Open Merge Request (Confirm MR status)",
        "DEV: Comment (Acknowledge fix and re-notify)",
        "DEV: Remove Container (Cleanup)",
        "Final Answer"
    ]
    return dev_fix_plan


def create_reviewer_plan(diff_comparison_params: Dict[str, str]):
    """
    Defines the sequence of tool calls for the Reviewer Agent 
    (Review -> Decide -> Act).
    """
    print("\n--- 🧑‍💼 PHASE 3 & 5: REVIEWER WORKFLOW PLAN (REVIEW & APPROVAL) ---")
    
    review_plan = [
        # Step 1: Initial review, get diff
        f"REV: Diff Code (Base: {diff_comparison_params['base']} -> Head: {diff_comparison_params['head']}))"

        # Step 2: Review Phase (Initial Check) & Rejection
        "REV: Open Merge Request (Check MR status/existence)",
        "REV: Comment (Acknowledge receipt, but this is done by the reviewer)",
        "REV: Approve/Reject MR (Rejection logic)",
        
        # Step 3: Fix Submitted - Re-check Diff
        f"REV: Diff Code (Base: {diff_comparison_params['base']} -> Head: {diff_comparison_params['head']})",        

        # Step 4: Reviewer Action (Approval)
        "REV: Open Merge Request (Re-check MR status after fix)",
        "REV: Approve/Reject MR (Approval logic)",
        "Final Answer"
    ]
    return review_plan


def run_agent_cycle(
    agent_name: str, 
    tools: List[Any], 
    plan: List[str], 
    local_repo_path: Path,
    mock_engine: MockEngine
):
    """
    Central function to simulate an agent's turn cycle.
    """
    print(f"\n=====================================================")
    print(f"⚙️ RUNNING {agent_name.upper()} WORKFLOW")
    print(f"=====================================================")

    # --- Mock Setup ---
    # The MockEngine needs the plan to be mapped to runnable code blocks.
    mocked_llm_steps = []
    
    # For better logging, we slightly adjust the mock structure based on the plan list
    for step in plan:
        if "SETUP: Create Volume" in step:
            mocked_llm_steps.append('<code>volume_mounts=create_volume()</code>')
        elif "SETUP: Start Container" in step:
            mocked_llm_steps.append('<code>container_id = start_container(image="alpine:3.19", volume_mounts_data=volume_mounts)</code>')
        elif "SETUP: Install Utilities (git)" in step:
            mocked_llm_steps.append('<code>install_utilities(container_id_or_container=container_id, utility_name="git")</code>')
        elif "SETUP: Clone Repository" in step:
            mocked_llm_steps.append(f'<code>clone_repository("{dummy_namespace_project}")</code>')
        elif "SETUP: Checkout Branch" in step:
            mocked_llm_steps.append(f'<code>checkout_branch("{DEV_SOURCE_BRANCH}")</code>')
        elif "DEV: List Directory" in step:
            mocked_llm_steps.append('<code>list_directory()</code>')
        elif "DEV: Read Code" in step:
            mocked_llm_steps.append('<code>read_code("{dummy_edit_file_path}")</code>')
        elif "DEV: Create File" in step:
            mocked_llm_steps.append(f'<code>create_file("{dummy_create_file_path}", "{dummy_create_file_content}")</code>')
        elif "DEV: Edit Code" in step:
            mocked_llm_steps.append(f'<code>edit_code("{dummy_edit_file_path}", \"\"\"{dummy_edited_java_file_content}\"\"\")</code>')
        elif "DEV: Check Status (Pre-commit check)" in step or "DEV: Check Status (Post-commit check)" in step:
            mocked_llm_steps.append('<code>git_status()</code>')
        elif "DEV: Git Commit" in step:
            mocked_llm_steps.append(f'<code>git_commit(["{dummy_edit_file_path}"], "{dummy_commit_message}")</code>')
        elif "DEV: Push Branch" in step:
            mocked_llm_steps.append('<code>git_push()</code>')
        elif "DEV: Open Merge Request (Create MR)" in step:
            mocked_llm_steps.append(f'<code>open_merge_request("{DEV_SOURCE_BRANCH}", "{DEV_TARGET_BRANCH}", "Feat: New Currency Domain Class")</code>')
        elif "DEV: Comment (Notify Reviewer)" in step:
            mocked_llm_steps.append(f'<code>comment(work_item_id="{ISSUE_IID}", comment_content="{dummy_comment}", recipient_type="REVIEWER")</code>')
        elif "DEV: Remove Container (Cleanup)" in step:
            mocked_llm_steps.append('<code>remove_container(container_id_or_container=container_id)</code>')
        elif "REV: Open Merge Request (Check MR status/existence)" in step:
            mocked_llm_steps.append(f'<code>open_merge_request("{DEV_SOURCE_BRANCH}", "{DEV_TARGET_BRANCH}", "Feat: New Currency Domain Class")</code>')
        elif "REV: Approve/Reject MR (Rejection logic)" in step:
            # This is the critical rejection step
            mocked_llm_steps.append(f'''<code>approve_or_reject_merge_request(issue_iid="{ISSUE_IID}", mr_iid="{MR_IID}", action_requested="REJECT", comment_content="{dummy_comment}")</code>''')
        elif "REV: Open Merge Request (Re-check MR status after fix)" in step:
            mocked_llm_steps.append(f'<code>open_merge_request("{DEV_SOURCE_BRANCH}", "{DEV_TARGET_BRANCH}", "Feat: New Currency Domain Class")</code>')
        elif "REV: Approve/Reject MR (Approval logic)" in step:
            # This is the critical approval step
            mocked_llm_steps.append(f'''<code>approve_or_reject_merge_request(issue_iid="{ISSUE_IID}", mr_iid="{MR_IID}", action_requested="APPROVE", comment_content=None)</code>''')
        elif "Final Answer" in step:
            mocked_llm_steps.append('''<code>final_answer("All done")</code>''')


    mocked_llm_steps = mocked_llm_steps

    # Initialize the mock engine
    mock_engine = MockEngine(mocked_llm_steps)
    
    # Initialize the agent
    agent = CodeAgent(
        tools=tools,
        stream_outputs=False,
        model=mock_engine,
        additional_authorized_imports=["pathlib"]
    )
    
    # Run the agent cycle
    agent.run("dummy")
    print("\n=====================================================")
    print("✅ Agent cycle completed successfully.")
    print("=====================================================")


if __name__ == "__main__":
    # --- Setup Dummy Content for the Flow ---
    # Mock content for the initial file creation/editing
    dummy_edited_java_file_content = """package ch.mzh.avclient.domain;
/**
 * Represents a currency domain object.
 */
public class CurrencyModel {
    private String currencyCode; 

    public CurrencyModel(String code) { 
        this.currencyCode = code;
    }

    public String getCurrencyCode() { return currencyCode; }
    public void setCurrencyCode(String code) { this.currencyCode = code; }
}"""

    # Mock content for the fixed, immutable file
    dummy_fix_java_file_content = """package ch.mzh.avclient.domain;
/**
 * Represents an immutable currency domain object.
 */
public final class CurrencyModel {
    private final String currencyCode;

    public CurrencyModel(String code) throws IllegalArgumentException {
        if (code == null || code.length() != 3) {
            throw new IllegalArgumentException("Invalid currency code format.");
        }
        this.currencyCode = code;
    }

    public String getCurrencyCode() { return currencyCode; }
    // Removed setCurrencyCode to enforce immutability
}"""
    
    # --- Initialization ---
    
    # Use a temporary directory for the simulation
    local_repository_path = Path(os.path.abspath("agent-data")).resolve()
    
    # 1. Initialize Docker Client (Must happen before tools)
    client = docker.from_env()
    
    # 2. Setup Developer Tools
    developer_tools = setup_developer_tools(client, local_repository_path)
    
    # 3. Setup Reviewer Tools
    reviewer_tools = [
        OpenMergeRequest(
            gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
            project_id=str(PROJECT_ID),
            access_token=GITLAB_TOKEN,
            default_title="Reviewer Default Title"
        ),
        Comment(
            gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
            project_id=str(PROJECT_ID),
            access_token=GITLAB_TOKEN
        ),
        ApproveOrReject(
            gitlab_url=f"http://{GITLAB_HOST}:{GITLAB_PORT}",
            project_id=str(PROJECT_ID),
            access_token=GITLAB_TOKEN
        ),
        GitDiff(local_repository_path)
    ]

    # --- A. RUN DEVELOPER FLOW (Developer's task: Create, Fix, and Push) ---
    
    dev_plan_initial = create_developer_plan(local_repository_path, dummy_edited_java_file_content, "")
    run_agent_cycle(
        agent_name="DEVELOPER", 
        tools=developer_tools, 
        plan=dev_plan_initial, 
        local_repo_path=local_repository_path, 
        mock_engine=MockEngine([]) # Mock engine will be rebuilt inside the function
    )

    # --- B. RUN REVIEWER FLOW (Reviewer's task: Reject, Wait, Approve) ---
    
    # The reviewer operates on the code left by the developer.
    review_diff_params = {
        'base': DEV_TARGET_BRANCH, 
        'head': DEV_SOURCE_BRANCH
    }
    review_plan = create_reviewer_plan(review_diff_params)
    run_agent_cycle(
        agent_name="REVIEWER", 
        tools=reviewer_tools, 
        plan=review_plan, 
        local_repo_path=local_repository_path, 
        mock_engine=MockEngine([])
    )
    
    # --- C. Simulate Developer Fix and Resubmission (The second half of the cycle) ---
    
    dev_plan_fix = create_developer_fix_plan(local_repository_path, dummy_fix_java_file_content)
    run_agent_cycle(
        agent_name="DEVELOPER (FIXER)", 
        tools=developer_tools, 
        plan=dev_plan_fix, 
        local_repo_path=local_repository_path, 
        mock_engine=MockEngine([])
    )