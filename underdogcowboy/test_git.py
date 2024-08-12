import os
import sys
import subprocess
import shutil

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(error.decode('utf-8'))
        sys.exit(1)
    return output.decode('utf-8').strip()

def git_diff_workflow(repo_path, file_path, changed_file_path):
    # Change to the repository directory
    os.chdir(repo_path)

    # Get the current branch name
    current_branch = run_command("git rev-parse --abbrev-ref HEAD")

    # Create a new branch for the changed file
    change_branch = "change-" + os.path.basename(file_path)
    run_command(f"git checkout -b {change_branch}")

    # Copy the changed file to the repository
    shutil.copy2(changed_file_path, file_path)

    # Stage and commit the changed file
    run_command(f"git add {file_path}")
    run_command(f'git commit -m "Add changes to {os.path.basename(file_path)}"')

    # Switch back to the original branch
    run_command(f"git checkout {current_branch}")

    # Start the merge operation
    run_command(f"git merge --no-commit --no-ff {change_branch}")

    print(f"Merge initiated. Please resolve conflicts (if any) and complete the merge.")
    print(f"You can now use 'git diff' to see the changes.")

if __name__ == "__main__":

    repo_path = "/Users/reneluijk/projects/UnderdogCowboy"
    file_path = "underdogcowboy/core/extractor.py"
    changed_file_path = "/Users/reneluijk/projects/UnderdogCowboy/test_change.py"

    if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
        print(f"Error: Repository path '{repo_path}' does not exist or is not a directory.")
        sys.exit(1)

    if not os.path.exists(os.path.join(repo_path, file_path)):
        print(f"Error: File '{file_path}' does not exist in the repository.")
        sys.exit(1)

    if not os.path.exists(changed_file_path):
        print(f"Error: Changed file '{changed_file_path}' does not exist.")
        sys.exit(1)

    git_diff_workflow(repo_path, file_path, changed_file_path)
