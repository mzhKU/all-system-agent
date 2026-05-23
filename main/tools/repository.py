import os
import gitlab
import git
import shutil
import json
from smolagents import Tool
from typing     import List
from pathlib    import Path

def clear_target(target: str, target_backup: str) -> bool:
    src_path = Path(target)
    backup_path = Path(target_backup)

    if not src_path.exists() or not src_path.is_dir():
        return
    backup_path.mkdir(parents=True, exist_ok=True)
    
    for item in src_path.iterdir():
        target_item_path = backup_path / item.name
        try:
            # Overwrite logic: remove conflicting destination path if it exists
            if target_item_path.exists():
                if target_item_path.is_dir():
                    shutil.rmtree(target_item_path)
                else:
                    target_item_path.unlink()
            shutil.move(str(item), str(target_item_path))
        except Exception as e:
            print(f"Warning: Failed to move {item.name} to backup: {e}")
            return False
    return True

class CloneRepository(Tool):
    name = "clone_repository"
    description = "This tool can be used to clone a git repository."
    output_type = "string"

    def __init__(self, host: str, port: int, access_token: str, local_repository_path: str, local_repository_path_backup:str):
        super().__init__()
        self.host = host
        self.port = port
        self.access_token = access_token
        self.local_repository_path = local_repository_path
        self.local_repository_path_backup = local_repository_path_backup

    @property
    def inputs(self):
        return {
            "np": {
                "type": "string",
                "description": "The namespace and project to clone, in the form <namespace>/<project>."
            },
        }
    
    def forward(self, np: str) -> str:
        """Clone a git repository."""
        try:
            if clear_target(target=self.local_repository_path, target_backup=self.local_repository_path_backup):
                clean_url = f"http://{self.host}:{self.port}/{np}"
                env = os.environ.copy()
                env["GIT_ASKPASS"] = "echo"
                env["GIT_TOKEN"] = self.access_token
                # repository_url_with_token = f"http://oauth2:{self.access_token}@{self.host}:{self.port}/{np}"
                git.Repo.clone_from(clean_url, self.local_repository_path)
        except Exception as e:
            return f"Error executing command: {e}"


class GitStatus(Tool):
    """
    Runs 'git status' to provide a comprehensive overview of the repository state.
    This allows the agent to know which files have been modified, staged, or are untracked.
    """
    name = "git_status"
    description = "Provides the current status of the repository (e.g., modified files, untracked files, changes staged for commit). This must be called after any code modification before attempting to commit."
    output_type = "string"

    def __init__(self, repository_path: Path):
        super().__init__()
        self.repository_path = repository_path
        self._repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        """Internal helper to initialize and validate the git repository connection."""
        try:
            self._repo = git.Repo(str(self.repository_path))
        except git.InvalidGitRepositoryError:
            print(f"Warning: Initializing GitStatus with invalid repository path: {self.repository_path}")
            self._repo = None
            
    @property
    def inputs(self):
        return {}

    def forward(self) -> str:
        """Executes 'git status' and returns a formatted, clean status report."""
        if self._repo is None:
            return "Error: Not a valid git repository. Cannot check status."

        print("\n[Git Status Tool] Running 'git status'...")
        try:
            status = self._repo.git.status()
            status_report = f"--- Repository Status Report ---\n"
            modified_files = self._repo.index.diff(None) # Check for modified files
            if modified_files:
                modified_list = [f"Modified: {d.a_path}" for d in modified_files]
                status_report += "--- Files Modified (Unstaged) ---\n"
                status_report += "\n".join(modified_list) + "\n"
            else:
                status_report += "--- Files Modified (Unstaged) ---\nNone detected. All files match the last commit.\n"            
            status_report += "\n--- Raw git status output for complete context ---\n"
            status_report += status
            return status_report
        except git.exc.GitCommandError as e:
            return f"Git Command Error: Failed to retrieve status. {e.stderr}"
        except Exception as e:
            return f"An unexpected error occurred while checking status: {e}"


class GitCommit(Tool):
    """
    Stages specified modified files and commits them to the repository 
    with a provided message. This is the final step before the work is considered saved.
    """
    name = "git_commit"
    description = "Stages a list of specified files and commits them to the repository with a message. Must be run with a list of files that were modified since the last status check."
    output_type = "string"

    def __init__(self, local_repository_path: Path):
        super().__init__()
        self.local_repository_path = local_repository_path
        self._repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        """Internal helper to initialize and validate the git repository connection."""
        try:
            self._repo = git.Repo(str(self.local_repository_path))
        except git.InvalidGitRepositoryError:
            print(f"Warning: Initializing GitCommit with invalid repository path: {self.local_repository_path}")
            self._repo = None
            
    # We pass the list of files and the message as arguments
    @property
    def inputs(self):
        return {
            "modified_files": {
                "type": "array",
                "description": "A list of file paths (relative to the repo root) that were modified and need to be committed. This list should come from the git_status tool output."
            },
            "commit_message": {
                "type": "string",
                "description": "A detailed, descriptive commit message summarizing the changes made (e.g., 'Feat: Implement new authentication flow')."
            }
        }
    
    def forward(self, modified_files: list[str], commit_message: str) -> str:
        """
        Stages all specified files and commits them using the provided message.
        """
        if self._repo is None:
            return "Error: Not a valid git repository. Cannot commit."

        if not modified_files:
            return "Warning: No files were specified for commitment. Nothing will be done."
        
        if not commit_message:
            return "Error: A commit message is mandatory. Please provide a summary of the changes."

        print("\n[Git Commit Tool] Starting commit sequence...")

        try:
            # 1. Staging Phase (git add)
            print("--- Staging files ---")
            for file_path in modified_files:
                try:
                    self._repo.index.add([file_path])
                    print(f"Staged: {file_path}")
                except Exception as e:
                    return f"Error staging file {file_path}: {e}"
            
            # 2. Commit Phase (git commit)
            print("--- Creating commit ---")
            # The commit function handles the creation of the commit object.
            commit = self._repo.index.commit(commit_message)
            
            return f"✅ Success: Committed changes to the repository.\nCommit Hash: {commit.hexsha[:7]}\nMessage: {commit_message}"

        except git.exc.GitCommandError as e:
            # Catch specific Git failures (e.g., no changes to commit)
            return f"Git Error: Failed to commit changes. Details: {e.stderr}"
        except Exception as e:
            return f"An unexpected error occurred during the commit process: {e}"


class CheckoutBranch(Tool):
    name = "checkout_branch"
    description = "Checks out an existing branch or creates and switches to a new one within the local repository."
    output_type = "string"

    def __init__(self, local_repository_path: str):
        super().__init__()
        self.local_repository_path = local_repository_path
        self._repo = None
        try:
            self._repo = git.Repo(local_repository_path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            print(f"Warning: Initializing CheckoutBranch with invalid repository path: {local_repository_path}")

    @property
    def inputs(self):
        return {
            "branch_name": {
                "type": "string",
                "description": "The name of the branch to check out or create."
            }
        }

    def forward(self, branch_name: str) -> str:
        """Executes the git checkout command cleanly."""
        if self._repo is None:
            return "Error: This tool was initialized with a path that is not a valid git repository."

        if not branch_name or not isinstance(branch_name, str):
            return "Error: Branch name must be a non-empty string."

        print(f"[Checkout Tool] Attempting to checkout branch: {branch_name} in {self.local_repository_path}")

        try:
            # Check if branch exists in local references
            if branch_name in self._repo.heads:
                self._repo.git.checkout(branch_name)
                return f"✅ Success: Switched to existing local branch '{branch_name}'."
            
            # If it does not exist locally, create and switch to it (-b flag equivalent)
            self._repo.git.checkout("-b", branch_name)
            return f"✅ Success: Created and switched to new branch '{branch_name}'."

        except git.GitCommandError as e:
            return f"Git Error: Failed to checkout branch '{branch_name}'. Details: {e.stderr.strip()}"
        except Exception as e:
            return f"An unexpected error occurred during checkout: {str(e)}"


class EditCode(Tool):
    """
    A tool to read, analyze, and write code files within the mounted repository volume.
    It operates on the physical file system path.
    """
    name = "edit_code"
    description = "Overwrites a specific file within the active repository directory." \
        "IMPORTANT: The provided file_path MUST contain the full, complete relative path" \
        "from the repository root (e.g., 'avclient/src/main/java/ch/mzh/avclient/domain/CurrencyModel.java')." \
        "Use this tool to make code changes before committing."
    output_type = "string"

    def __init__(self, local_repository_path: Path):
        super().__init__()
        self.local_repository_path = local_repository_path
        
    @property
    def inputs(self):
        return {
            "file_path": {
                "type": "object",
                "description": "The path to the file relative to the repository root, including ALL necessary project directories (e.g., 'avclient/src/main/java/ch/mzh/avclient/domain/CurrencyModel.java'). This must be the full, correct relative path."
            },
            "content": {
                "type": "string",
                "description": "The full content string to write to the file. This is used for overwriting the file entirely."
            }
        }
    
    def forward(self, file_path: str, content: str) -> str:
        """
        Handles the logic for overwriting the file content.
        """
        target_path = self.local_repository_path / Path(file_path)
        if not target_path.exists():
            return f"Error: The specified file path does not exist in the repository: {file_path}. Please verify the full, correct path."

        try:
            target_path.write_text(content)
            return f"✅ Success: Overwrote the content of '{file_path}' in the repository."
        except Exception as e:
            return f"Error: Could not overwrite the file '{file_path}'. Check permissions. Details: {e}"


class CreateFile(Tool):
    """
    A tool to create new files within the mounted repository volume.
    Use this tool when a file does not currently exist.
    """
    name = "create_file"
    description = "Creates a new file at the specified path relative to the repository root. IMPORTANT: The provided file_path MUST contain the full, complete relative path from the repository root, including ALL necessary project directories (e.g., 'avclient/src/main/java/...')."
    output_type = "string"

    def __init__(self, local_repository_path: Path):
        super().__init__()
        self.local_repository_path = local_repository_path
        
    @property
    def inputs(self):
        return {
            "file_path": {
                "type": "object",
                "description": "The path to the file relative to the repository root, including ALL necessary project directories (e.g., 'avclient/src/main/java/ch/mzh/avclient/domain/CurrencyModel.java')."
            },
            "content": {
                "type": "string",
                "description": "The full content string to write to the new file. If empty, an empty file is created."
            }
        }
    
    def forward(self, file_path: str, content: str) -> str:
        """
        Handles the logic for creating the file and writing the content.
        """
        target_path = self.local_repository_path / Path(file_path)

        # Check if the directory structure exists
        directory_path = target_path.parent
        if not directory_path.exists():
            try:
                # Attempt to create the necessary directory structure
                # This assumes the directory structure *must* be created relative to the mount point.
                directory_path.mkdir(parents=True, exist_ok=True)
                print(f"Info: Created necessary directory structure at: {directory_path}")
            except Exception as e:
                return f"Error: Could not create necessary directory structure for '{file_path}'. Check permissions. Details: {e}"

        try:
            target_path.write_text(content)
            return f"✅ Success: Created and wrote content to the new file '{file_path}' in the repository."
        except Exception as e:
            return f"Error: Could not create or write to the file '{file_path}'. Check permissions. Details: {e}"


class ReadCode(Tool):
    """
    Reads and analyzes the current content of a specific file in the repository.
    This allows the agent to understand existing code before making changes.
    """
    name = "read_code" 
    description = "Reads the entire content of a specified file in the repository for analysis and context." \
    "Returns the code content."
    output_type = "string"

    def __init__(self, local_repository_path: Path):
        """
        Initializes the ReadCode tool.
        """
        super().__init__()
        self.local_repository_path = local_repository_path

    @property
    def inputs(self):
        return {
            "file_path": {
                "type": "string",
                "description": "The path to the file relative to the repository root (e.g., 'src/utils.py')."
            }
        }

    def forward(self, file_path: str) -> str:
        """
        Reads and returns the content of the specified file.
        """
        target_path = self.local_repository_path / Path(file_path)
        
        if not target_path.exists():
            return f"Error: The file path does not exist in the repository: {file_path}"
        
        try:
            content = target_path.read_text()
            return f"```{content}\n```"
        except Exception as e:
            return f"Error reading file '{file_path}'. Details: {e}"


class ListCode(Tool):
    """
    Traverses and lists the file and directory structure of the root of the 
    cloned repository, providing an overview of available files and folders.
    """
    name = "list_directory"
    description = "Lists the full file and directory tree structure within the current repository volume. Use this tool first to map out the file structure before attempting to read or edit files. The output provides relative paths necessary for other tools."
    output_type = "string"

    def __init__(self, local_repository_path: Path):
        """
        Initializes the tool with the absolute path to the root of the repository.
        """
        super().__init__()
        self.local_repository_path = local_repository_path

    @property
    def inputs(self):
        return {}

    def forward(self) -> str:
        """
        Uses os.walk to recursively traverse and list the directory structure.
        """
        print(f"\n[Overview Tool] Scanning repository structure at: {self.local_repository_path}")
        
        # Use a list to collect all file paths
        file_list: List[str] = []
        
        # os.walk provides the current directory, subdirectory list, and file list
        for root, dirs, files in os.walk(self.local_repository_path):
            current_path = Path(root)
            
            # Dont list .git directory
            if ".git" in current_path.parts:
                continue

            # Calculate the relative path from the repository root
            # This is essential for the LLM to use consistent paths later.
            relative_root = Path(root).relative_to(self.local_repository_path)
            
            # 1. Add the current directory marker
            # This helps the LLM understand the folder structure
            if str(relative_root) != ".":
                file_list.append(f"--- /{relative_root} ---")
            
            # 2. List all files found in the current directory
            for file in files:
                relative_path = str(Path(relative_root) / file)
                file_list.append(f"  📄 {relative_path}")
            
            # 3. List all subdirectories found
            for directory in dirs:
                relative_path = str(Path(relative_root) / directory)
                file_list.append(f"  📂 {relative_path}/")

        if not file_list:
             return "The directory appears empty or is inaccessible."

        # Join the collected list into a single, formatted output
        return "\n".join(file_list)


class PushBranch(Tool):
    """
    Pushes the local branch and commits to the remote repository (e.g., 'origin').
    This is the action required to make the committed work visible to collaborators.
    """
    name = "git_push"
    description = "Pushes the current local branch and all committed changes to the remote repository (usually 'origin'). Must be run after git_commit."
    output_type = "string"

    def __init__(self, local_repository_path: Path, access_token: str):
        super().__init__()
        self.local_repository_path = local_repository_path
        self.access_token = access_token
        self._repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        """Internal helper to initialize and validate the git repository connection."""
        try:
            self._repo = git.Repo(str(self.local_repository_path))
        except git.InvalidGitRepositoryError:
            print(f"Warning: Initializing PushBranch with invalid repository path: {self.local_repository_path}")
            self._repo = None
            
    @property
    def inputs(self):
        return {}

    def forward(self) -> str:
        """
        Executes 'git push' command to synchronize local commits with the remote.
        """
        if self._repo is None:
            return "Error: Not a valid git repository. Cannot push changes."

        print("\n[Git Push Tool] Attempting to push changes to the remote repository...")

        # Set the environment variables required for git to authenticate using the token
        env = os.environ.copy()
        env["GIT_ASKPASS"] = "echo"
        env["GIT_TOKEN"] = self.access_token

        try:
            # Determine the current branch name
            current_branch = self._repo.active_branch.name
            remote_name = "origin"
            
            # Attempt to push, explicitly setting the upstream branch
            print(f"Executing: git push --set-upstream {remote_name} {current_branch}")
            
            # Use the git command interface to pass the environment variables
            self._repo.git.push(
                remote_name, 
                current_branch,
                set_upstream=True,
                env=env
            )
            
            return f"✅ Success: Successfully pushed all commits from the local branch '{current_branch}' to the '{remote_name}' remote and set the upstream branch."
        except git.exc.GitCommandError as e:
            # This usually means authentication failure, network error, or nothing to push.
            error_output = e.stderr
            if "Updates were rejected" in error_output:
                return "Push Error: The remote branch was updated by someone else. Please pull the latest changes and try committing again."
            
            if "Authentication failed" in error_output or "Permission denied" in error_output:
                 return f"Authentication Error: Failed to push. Please verify the access token and repository permissions. Details: {error_output}"
            
            return f"Git Push Error: Failed to push changes. Check credentials or repository name. Details: {error_output}"
        except Exception as e:
            return f"An unexpected error occurred during the push process: {e}"


class GeneratePlan(Tool):
    """
    Generates a structured, executable plan based on the user's task description,
    identifying which files need reading, editing, and which branches must be used.
    """
    name = "generate_plan"
    description = "The mandatory first step when receiving a task. It takes a work item description and outputs a JSON plan detailing all necessary steps, file paths, and intended actions (READ, EDIT, CHECKOUT)."
    output_type = "object"

    @property
    def inputs(self):
        return {
            "work_item_description": {
                "type": "string",
                "description": "The work item given by the user."
            }
        }
   
    # Note: This tool is intentionally stateless and takes the raw input.
    # The actual "intelligence" resides in the LLM mapping the input string to this structure.
    def forward(self, work_item_description: str) -> str:
        """
        In a real system, this method might call a specialized LLM prompt endpoint
        that enforces a strict JSON schema output based on the description.
        For a simulated tool, we simply acknowledge the request.
        """
        print(f"\n[Planner Tool] Analyzing work item request: '{work_item_description}'...")
        
        # A real implementation would use Pydantic/JSON schema validation here.
        # For demonstration, we confirm the action and guide the agent.
        
        return json.dumps({
            "status": "PLAN_SUCCESSFUL",
            "message": f"Plan generated for task: '{work_item_description}'. The agent will now proceed by calling list_directory() to map the file structure.",
            "plan_steps": [
                {"action": "list_directory", "context": "Get overview of the repo structure."},
                {"action": "read_code", "context": "Read the main entry point file in the relevant directory."},
                {"action": "edit_code", "context": "Apply the necessary functional changes to the code."},
                {"action": "commit_and_push", "context": "Finalize the changes."}
            ]
        }, indent=2)


class OpenMergeRequest(Tool):
    """
    Creates or verifies a Merge Request (MR) on GitLab. If an MR already exists 
    for the source branch, this tool retrieves and reports its details instead of failing.
    """
    name = "open_merge_request"
    description = "Creates a Pull Request/Merge Request on GitLab. This tool checks if an MR already exists for the source branch and, if so, reports its details. If it does not exist, a new MR is created. Requires the source branch, target branch, and a title."
    output_type = "string"

    def __init__(self, gitlab_url: str, project_id: str, access_token: str, default_title: str):
        super().__init__()
        self.gitlab_url = gitlab_url
        self.access_token = access_token
        self.project_id = project_id
        self.default_title = default_title
        self._gl_client = None

    @property
    def inputs(self):
        return {
            "source_branch": {
                "type": "string",
                "description": "The name of the branch that contains the new work (the branch that was just pushed)."
            },
            "target_branch": {
                "type": "string",
                "description": "The stable branch that the changes should be merged into (e.g., 'main')."
            },
            "custom_title": {
                "type": "string",
                "description": "Optional custom title for the merge request. If empty, a default title will be used."
            }
        }
    
    def forward(self, source_branch: str, target_branch: str, custom_title: str) -> str:
        """
        Connects to GitLab and checks for or creates the Merge Request.
        """
        if not self.gitlab_url or not self.access_token or not self.project_id:
            return "Error: OpenMergeRequest could not be initialized. Missing GitLab URL, Token, or Project ID."

        title = custom_title if custom_title else self.default_title
        
        try:
            # 1. Initialize the GitLab client
            gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token, ssl_verify=False, keep_base_url=True)
            gl.auth()
            project = gl.projects.get(self.project_id)

            if not project:
                return f"Error: Could not find project with ID {self.project_id}."

            # --- CHECK STAGE ---
            # Check for existing open merge requests for this source branch
            mr_list = project.mergerequests.list(source_branch=source_branch, state="opened")
            if mr_list:
                existing_mr = mr_list[0]

                # TODO: Make this generic
                # Statically construct the URL using class attributes and the MR IID
                base = self.gitlab_url.rstrip("/")
                repo_path = "mzhku/all-system-development"
                corrected_url = f"{base}/{repo_path}/-/merge_requests/{existing_mr.iid}"         

                return (f"✅ Found Existing MR: A Merge Request already exists for '{source_branch}' "
                        f"targeting '{target_branch}'. Details: "
                        f"MR ID: {existing_mr.iid}, Title: '{existing_mr.title}', "
                        f"Link: {corrected_url}")

            # --- CREATION STAGE ---
            try:
                mr = project.mergerequests.create({
                    'source_branch': source_branch,
                    'target_branch': target_branch,
                    'title': title,
                })
                web_url = getattr(mr, 'web_url', 'Unknown URL')
                iid = getattr(mr, 'iid', 'Unknown IID')
                return f"✅ Success: Merge Request created! View it here: {web_url} (IID: {iid})."

            except gitlab.exceptions.GitlabCreateError as e:
                error_message = str(e)
                if "Another open merge request already exists" in error_message:
                    return (f"⚠️ Status Alert: A Merge Request already exists for '{source_branch}' and cannot be duplicated. "
                            f"No action taken. Details: {error_message}")
                return f"❌ Failed to create Merge Request: {error_message}"

        except gitlab.exceptions.GitlabAuthenticationError:
            return "❌ Authentication failed. Check your access token and project permissions."
        except Exception as e:
            return f"❌ An unexpected error occurred during the merge request process: {str(e)}"


class Comment(Tool):
    """
    Posts a standardized comment to the original GitLab work item (issue). 
    The tool automatically prefixes the comment based on the specified recipient role.
    """
    name = "comment"
    description = "Posts a structured comment to the original work item (issue) to notify specific roles (Developer, Reviewer, Human) or provide general updates. The comment will be automatically prefixed with '@AGENT_DEV', '@AGENT_REV', or '@HUMAN' based on the specified recipient type."
    output_type = "string"

    def __init__(self, gitlab_url: str, project_id: str, access_token: str):
        super().__init__()
        self.gitlab_url = gitlab_url
        self.access_token = access_token
        self.project_id = project_id

    @property
    def inputs(self):
        return {
            "work_item_id": {
                "type": "string",
                "description": "The internal ID (IID) of the original issue/work item to comment on. This ID is used to locate the specific issue in the project."
            },
            "comment_content": {
                "type": "string",
                "description": "The primary content of the message to be left in the comment. Do not include the prefix in this field."
            },
            "recipient_type": {
                "type": "string",
                "description": "The role being addressed for the comment. Must be one of: 'DEVELOPER' (for @AGENT_DEV), 'REVIEWER' (for @AGENT_REV), or 'HUMAN' (for @HUMAN). The tool will automatically apply the correct prefix."
            }
        }
    
    def forward(self, work_item_id: str, comment_content: str, recipient_type: str) -> str:
        """
        Constructs the full comment body with the appropriate prefix and posts it to GitLab.
        """
        
        # 1. Validate and Prefix the Comment
        prefix_map = {
            "DEVELOPER": "@AGENT_DEV",
            "REVIEWER": "@AGENT_REV",
            "HUMAN": "@HUMAN"
        }

        prefix = prefix_map.get(recipient_type.upper())
        
        if not prefix:
            return f"Error: Invalid recipient type '{recipient_type}'. Must be one of: DEVELOPER, REVIEWER, or HUMAN."

        # Construct the final, fully formatted comment body
        full_comment_body = f"{prefix} {comment_content}"

        # 2. Initialize the GitLab client
        if not self.gitlab_url or not self.access_token or not self.project_id:
            return "Error: Comment tool could not be initialized. Missing GitLab URL, Token, or Project ID."

        try:
            gl = gitlab.Gitlab(self.gitlab_url, private_token=self.access_token, ssl_verify=False, keep_base_url=True)
            gl.auth()
            project = gl.projects.get(self.project_id)

            if not project:
                return f"Error: Could not find project with ID {self.project_id}."

            # 3. Check and Post the Comment
            try:
                issue = project.issues.get(work_item_id)
            except gitlab.exceptions.GitlabCreateError:
                return f"Error: Could not find the specified issue (IID: {work_item_id}) in this project. Please verify the ID."
            
            # Use the API to append the comment
            issue.notes.create({'body': full_comment_body})
            
            return f"✅ Success: Comment successfully posted to Issue {work_item_id} with the prefix '{prefix}'. The full message sent was:\n\n---\n{full_comment_body}\n---"
            
        except gitlab.exceptions.GitlabAuthenticationError:
            return "❌ Authentication failed. Check your access token and project permissions (Ensure the token has 'api' scope for reading and writing issues)."
        except gitlab.exceptions.GitlabCreateError as e:
            return f"❌ Failed to post comment due to GitLab error. Check issue ID ({work_item_id}) and project visibility. Details: {e.error_message}"
        except Exception as e:
            return f"❌ An unexpected error occurred during the comment posting process: {e}"

