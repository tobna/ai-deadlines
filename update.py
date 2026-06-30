import os
import re
import subprocess
from datetime import datetime

THIS_DIR = os.path.dirname(__file__)
REPO_URL = "https://github.com/tobna/ai-deadlines"
GIT_USER = "tobna"

# A git credential helper that reads the token from the environment at call time, so the
# secret never appears in argv (world-readable via /proc and shell history) the way it did
# when interpolated into an `os.system("git push https://user:TOKEN@...")` string.
_CREDENTIAL_HELPER = '!f() { echo "username=$GIT_USERNAME"; echo "password=$GIT_TOKEN"; }; f'


def load_token():
    token_file = os.path.join(THIS_DIR, ".gittkn")
    if not os.path.isfile(token_file):
        return None
    with open(token_file) as f:
        return f.read().strip()


def run(args):
    return subprocess.run(args, cwd=THIS_DIR, check=False)


def git_authenticated(git_args, token):
    """Run a git command with credentials supplied via the environment, not argv."""
    env = {**os.environ, "GIT_USERNAME": GIT_USER, "GIT_TOKEN": token}
    return subprocess.run(
        ["git", "-c", f"credential.helper={_CREDENTIAL_HELPER}", *git_args],
        cwd=THIS_DIR,
        env=env,
        check=False,
    )


def update_readme_badge(count):
    readme = os.path.join(THIS_DIR, "README.md")
    alt = "Status: Conferences Tracked"
    badge = f"https://img.shields.io/badge/Conferences%20Tracked-{count}-blue?logo=kdenlive&logoColor=white"
    with open(readme) as f:
        content = f.read()
    content = re.sub(rf"\[!\[{re.escape(alt)}\]\(.*?\)\]", f"[![{alt}]({badge})]", content)
    with open(readme, "w") as f:
        f.write(content)


def main():
    token = load_token()
    if token:
        git_authenticated(["pull", REPO_URL], token)

    print("run update script", flush=True)
    run(["python3", "-m", "aideadlines.update_data", "--online"])

    print("convert data to json", flush=True)
    run(["python3", "-m", "aideadlines.data_to_json"])

    if token:
        conferences_tracked = [f for f in os.listdir(os.path.join(THIS_DIR, "conferences")) if f.endswith(".yaml")]
        update_readme_badge(len(conferences_tracked))
        run(["git", "add", "."])
        run(["git", "commit", "-m", f"Update conference data at {datetime.now().isoformat()}"])
        git_authenticated(["push", REPO_URL], token)


if __name__ == "__main__":
    main()
