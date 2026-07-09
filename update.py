import os
import re
import subprocess
from datetime import datetime

THIS_DIR = os.path.dirname(__file__)
REPO_URL = "https://github.com/tobna/ai-deadlines"
GIT_USER = "tobna"
# Same file loguru's ERROR sink writes to (log_config.py). ponytail: assumes CWD == repo root,
# which is true for make_website.sh; that is the only deploy entry point.
ERROR_FILE = os.path.join(THIS_DIR, "error.log")

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


def error_line_count():
    if not os.path.isfile(ERROR_FILE):
        return 0
    with open(ERROR_FILE) as f:
        return sum(1 for _ in f)


def main():
    open(ERROR_FILE, "w").close()  # fresh per-run log so the status marker reflects only this run
    failed_steps = 0
    try:
        token = load_token()
        if token:
            git_authenticated(["pull", REPO_URL], token)

        print("run update script", flush=True)
        failed_steps += run(["python3", "-m", "aideadlines.update_data", "--online"]).returncode != 0

        print("validate conference data", flush=True)
        if run(["python3", "-m", "aideadlines.validate"]).returncode != 0:
            print("conference validation failed; aborting before json conversion and commit", flush=True)
            failed_steps += 1
            return

        print("convert data to json", flush=True)
        failed_steps += run(["python3", "-m", "aideadlines.data_to_json"]).returncode != 0

        if token:
            conferences_tracked = [f for f in os.listdir(os.path.join(THIS_DIR, "conferences")) if f.endswith(".yaml")]
            update_readme_badge(len(conferences_tracked))
            run(["git", "add", "."])
            run(["git", "commit", "-m", f"Update conference data at {datetime.now().isoformat()}"])
            git_authenticated(["push", REPO_URL], token)
    finally:
        # Machine-readable last line for Uptime Kuma: keyword monitor on "=== PIPELINE OK ===".
        errors = error_line_count()
        if errors == 0 and failed_steps == 0:
            print("=== PIPELINE OK ===", flush=True)
        else:
            print(f"=== PIPELINE FAILED: {errors} error(s), {failed_steps} failed step(s) ===", flush=True)


if __name__ == "__main__":
    main()
