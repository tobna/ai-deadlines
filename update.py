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
    failed_steps = []

    def check(step, result):
        """Record a failed step, with a red line that lands in status.html next to its output."""
        if result.returncode != 0:
            print(f"\x1b[1;31mERROR: {step} failed (exit code {result.returncode})\x1b[0m", flush=True)
            failed_steps.append(step)
        return result.returncode == 0

    try:
        token = load_token()
        if token:
            check("git pull", git_authenticated(["pull", REPO_URL], token))

        print("run update script", flush=True)
        check("update data", run(["python3", "-m", "aideadlines.update_data", "--online"]))

        print("validate conference data", flush=True)
        if not check("validate", run(["python3", "-m", "aideadlines.validate"])):
            print("conference validation failed; aborting before json conversion and commit", flush=True)
            return

        print("convert data to json", flush=True)
        check("convert to json", run(["python3", "-m", "aideadlines.data_to_json"]))

        if token:
            conferences_tracked = [f for f in os.listdir(os.path.join(THIS_DIR, "conferences")) if f.endswith(".yaml")]
            update_readme_badge(len(conferences_tracked))
            run(["git", "add", "."])
            run(["git", "commit", "-m", f"Update conference data at {datetime.now().isoformat()}"])  # 1 = nothing new
            check("git push", git_authenticated(["push", REPO_URL], token))
    finally:
        # Machine-readable last line for Uptime Kuma: keyword monitor on "=== PIPELINE OK ===".
        errors = error_line_count()
        if errors == 0 and not failed_steps:
            print("=== PIPELINE OK ===", flush=True)
        else:
            failed = ", ".join(failed_steps) or "none"
            print(f"=== PIPELINE FAILED: {errors} error(s), failed step(s): {failed} ===", flush=True)


if __name__ == "__main__":
    main()
