
from typing import Optional
from pathlib import Path
from smolagents import Tool

import gitlab
import requests

def search_codebase(query: str, path: str = "."):
    import os
    path_obj = Path(path)
    matches = []

    for file_path in path_obj.rglob("*"):
        if file_path.name.startswith('__') or file_path.name in ['test_*.py']:
            continue
        if str(file_path).endswith('.py'):
            try:
                content = file_path.read_text(encoding='utf-8')
                if len(content) < 5000:
                    relative = file_path.relative_to(path_obj)
                    matches.append(f"File: `{relative}`\n{content}")
            except:
                continue

    return "\n\n".join(matches)

def load_codebase(root_dir: str, repo_root: Optional[str] = None) -> str:
    root = Path(root_dir)
    IGNORE_DIRS = {
        'node_modules', '__pycache__', '.git', 'venv', 'env', '.venv',
        'build', 'dist', '.idea', '.vscode', 'coverage', 'migrations', 'tests'
    }

    ALLOWED_EXTENSIONS = {'.py', '.pyi', '.md'}

    context_parts = []
    file_count = 0
    total_tokens_estimate = 0
    tokens_per_line = 30

    print(f"Scanning repository at: {root}")

    for path in root.rglob('*'):
        if path.is_dir() and path.name in IGNORE_DIRS:
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            line_token_count = len(lines) * tokens_per_line

            current_estimated_tokens = total_tokens_estimate + line_token_count
            if current_estimated_tokens > 32000:
                print(f"⚠️ Context budget nearly exceeded ({current_estimated_tokens} tokens). Stopping scan of {path}.")
                break
            
            clean_content = "\n".join([l.strip() for l in lines if l.strip() and not l.startswith('# !')])

            relative_path = path.relative_to(root).as_posix()
            header = f"## `{relative_path}`"
            context_parts.append(f"{header}\n{clean_content}")

            file_count += 1
            total_tokens_estimate += line_token_count

        except UnicodeDecodeError:
            # Skip binary files
            continue
    
    if file_count == 0:
        return "No source files found"
    
    final_context = "--- COMPLETE CODEBASE ---"
    final_context += "\n".join(context_parts) + "\n\n"
    final_context += "--- END CODEBASE ---"
    final_context += f"\n*Stats: Found {file_count} files.*"

    return final_context

class CodebaseReaderTool(Tool):
    name = "codebase_reader"
    description = ("Read and retrieve code files from the repository."
                   "This tool returns the content of Python files in Markdown format, "
                   "including path headers for context tracking."
    )

    def _forward(self, root_dir: str, repo_root: Optional[str] = None):
        return load_codebase(root_dir, repo_root)

class RemoteCodebaseReader(Tool):
    name = "remote_codebase_reader"
    description = (
        "Read Java source files from a remote GitLab repository directly into memory. "
        "This tool fetches files via the GitLab API without needing a local clone. "
        "Returns files as markdown code blocks with relative paths."
    )
    output_type = "string"

    def __init__(
        self,
        gitlab_url: str,
        access_token: str,
        repo_name: str,
        max_tokens: int = 200_000,
        file_extension_filter: str = ".java"
    ):
        super().__init__()

        self.gitlab_url = gitlab_url
        self.access_token = access_token
        self.repo_name = repo_name
        self.max_tokens = max_tokens
        self.file_extension_filter = file_extension_filter
        self.current_tokens = 0
        self.api_headers = {"PRIVATE-TOKEN": access_token}
        self.is_initialized = True

    @property
    def inputs(self):
        return {
            "max_files": {
                "nullable": True,
                "type": "integer",
                "description": "Maximum number of Java files to read to avoid token overflow"
            },
            "root_dir": {
                "nullable": True,
                "description": "Optional subdirectory to start from",
                "type": "string"
            }
        }

    def forward(self, root_dir: Optional[str] = None, max_files: Optional[int] = 100) -> str:
        """
        Read files from the remote GitLab repository into memory.

        Parameters:
            root_dir: Optional subdirectory to start from
            max_files: Maximum number of files to read to avoid token overflow

        Returns:
            Markdown-formatted file contents
        """
        all_code = ""
        java_files = []

        try:
            gl = gitlab.Gitlab(self.gitlab_url, self.access_token, keep_base_url=True)
            project = gl.projects.get(1) # TODO: use repo_name instead of project id
            all_files = project.repository_tree(ref="main", recursive=True, keep_base_url=True, get_all=True) # TODO: argument for 'ref'
            java_files = [f for f in all_files if f['type']=='blob' and f['name'].lower().endswith(".java")]
        except Exception as e:
            return f"Error connecting to GitLab repository: {str(e)}"
        
        for jf in java_files:
            java_code = project.files.get(jf['path'], ref="main").decode().decode("utf-8", errors="replace")
            java_code_stripped = ""
            for l in java_code.split("\n"):
                if not l.strip():
                    continue
                if l.startswith("import"):
                    continue
                java_code_stripped += l + "\n"
            all_code += "\n"
            all_code += f"File: {jf['path']}:\n"
            all_code += java_code_stripped
            all_code += "\n"

        return all_code


if __name__ == "__main__":
    context = load_codebase('.')
    print(context)