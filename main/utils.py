import gitlab

def cleanup_gitlab_project(gitlab_url, private_token, project_id, protected_branch='main'):
    """
    Deletes all branches except the protected branch and all merge requests in a GitLab project.
    """
    gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
    try:
        project = gl.projects.get(project_id)
    except gitlab.exceptions.GitlabAuthenticationError:
        print("Authentication failed. Check the private token.")
        return
    except gitlab.exceptions.GitlabGetError:
        print(f"Project with ID {project_id} not found.")
        return

    # Delete work items
    issues = project.issues.list(get_all=True)
    for issue in issues:
        try:
            project.issues.delete(issue.iid)
            print(f"Deleted issue #{issue.iid}: {issue.title}")
        except Exception as e:
            print(f"Failed to delete issue #{issue.iid}: {e}")

    # Delete branches
    branches = project.branches.list(all=True)
    for branch in branches:
        if branch.name != protected_branch:
            try:
                project.branches.delete(branch.name)
                print(f"Deleted branch: {branch.name}")
            except Exception as e:
                print(f"Failed to delete branch {branch.name}: {e}")

    # Delete merge requests
    merge_requests = project.mergerequests.list(all=True)
    for mr in merge_requests:
        try:
            mr.delete()
            print(f"Deleted merge request: {mr.iid}")
        except Exception as e:
            print(f"Failed to delete merge request {mr.iid}: {e}")

if __name__ == "__main__":
    # Configuration requirements
    GITLAB_HOST = "100.122.48.109"
    GITLAB_PORT = 8081
    GITLAB_TOKEN_MAINTAINER_API = 'glpat-G1fVHSZ2erhAolGMXmsc5W86MQp1OmEH.01.0w0hnniho'
    PROJECT_ID = 1  # Replace with actual Project ID
    MAIN_BRANCH_NAME = 'main'

    cleanup_gitlab_project(
        f"http://{GITLAB_HOST}:{GITLAB_PORT}",
        GITLAB_TOKEN_MAINTAINER_API,
        PROJECT_ID,
        MAIN_BRANCH_NAME
    )
