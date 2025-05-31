import os
from datetime import datetime

this_dir = os.path.dirname(__file__)

git_tkn_file = os.path.join(this_dir, ".gittkn")
if os.path.isfile(git_tkn_file):
    with open(git_tkn_file, "r") as f:
        git_tkn = f.read().strip()
    os.system(f"git pull https://tobna:{git_tkn}@github.com/tobna/ai-deadlines")
else:
    git_tkn = None

update_script = os.path.join(this_dir, "src", "update_data.py")
# autoupdate_log = os.path.join(this_dir, "autoupdate.log")
print(f"run update script at {update_script}", flush=True)
os.system(f"python3 {update_script} --online")


to_json_script = os.path.join(this_dir, "src", "data_to_json.py")
print("convert data to json", flush=True)
os.system(f"python3 {to_json_script}")

if git_tkn is not None:
    os.system("git add .")
    os.system(f"git commit -m 'Update conference data at {datetime.now().isoformat()}'")
    os.system(f"git push https://tobna:{git_tkn}@github.com/tobna/ai-deadlines")
