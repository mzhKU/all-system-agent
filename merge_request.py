import gitlab
import sys

# === CONFIGURATION ===
GITLAB_URL = "https://gitlab.com"  # Change to your GitLab instance URL
PRIVATE_TOKEN = "YOUR_PERSONAL_ACCESS_TOKEN"  # Must have 'api' scope
PROJECT_ID = 12345678  # Numeric project ID (not the name)
SOURCE_BRANCH = "feature-branch"
TARGET_BRANCH = "main"
MR_TITLE = "Add new feature"
MR_DESCRIPTION = "This merge request adds the new feature as discussed."

def create_merge_request():
    # Validate required fields
    if not all([GITLAB_URL, PRIVATE_TOKEN, PROJECT_ID, SOURCE_BRANCH, TARGET_BRANCH, MR_TITLE]):
        print("Error: Missing required configuration values.")
        sys.exit(1)

    try:
        # Connect to GitLab
        gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)

        # Get the project
        project = gl.projects.get(PROJECT_ID)

        # Create the merge request
        mr = project.mergerequests.create({
            'source_branch': SOURCE_BRANCH,
            'target_branch': TARGET_BRANCH,
            'title': MR_TITLE,
            'description': MR_DESCRIPTION
        })

        print(f"✅ Merge Request created successfully!")
        print(f"MR ID: {mr.iid}")
        print(f"MR URL: {mr.web_url}")

    except gitlab.exceptions.GitlabAuthenticationError:
        print("❌ Authentication failed. Check your token and permissions.")
    except gitlab.exceptions.GitlabCreateError as e:
        print(f"❌ Failed to create MR: {e.error_message}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    create_merge_request()
