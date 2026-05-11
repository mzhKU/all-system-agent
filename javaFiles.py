import gitlab
from gitlab.v4.objects import Project

gitlab_url="http://localhost:8081"
token="glpat-dwoSrd4QERnkDfamNdS3lG86MQp1OjQH.01.0w07rm1a9"
project_id="1"
branch="main"

all_code = ""
java_files = []

gl = gitlab.Gitlab(gitlab_url, token, keep_base_url=True)
project = gl.projects.get(1) # TODO: use repo_name instead of project id
all_files = project.repository_tree(ref="main", recursive=True, get_all=True) # TODO: argument for 'ref'
java_files = [f for f in all_files if f['type']=='blob' and f['name'].lower().endswith(".java")]


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



print(all_code)


# # >>> type(f0)
# # <class 'gitlab.v4.objects.files.ProjectFile'>
# # >>> decoded_bytes = f0.decode()
# # >>> decoded_text = decoded_bytes.decode("utf-8", errors="replace")
# # >>> print(decoded_text)