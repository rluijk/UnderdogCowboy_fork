import subprocess
import os

def search_repos(repos, search_term, file_filters):
    """
    Search for a term in specified git repositories with dynamic file filters.

    :param repos: List of repository paths
    :param search_term: Term to search for
    :param file_filters: List of file extensions to filter (e.g., ['json', 'py'])
    """
    for repo in repos:
        print(f"\nSearching in repository: {repo}")
        try:
            # Change to the repo directory
            os.chdir(repo)

            # Construct the git grep command
            filters = " ".join([f"'*.{ext}'" for ext in file_filters])
            command = f"git grep -F '{search_term}' $(git rev-list --all) -- {filters}"

            # Execute the command and capture the output
            result = subprocess.run(command, shell=True, text=True, capture_output=True)

            # Print the output or handle errors
            if result.stdout:
                print(result.stdout)
            elif result.stderr:
                print(f"Error in repo {repo}: {result.stderr}")
            else:
                print("No results found.")

        except Exception as e:
            print(f"Failed to search in {repo}: {e}")

if __name__ == "__main__":
    # Define repositories and filters
    repositories = [
        "/Users/reneluijk/llm_dialogs",
        "/Users/reneluijk/projects/UnderdogCowboy",
        "/Users/reneluijk/obsidian_vaults/workshop/workshop-materials",
        "/users/reneluijk/.underdogcowboy/agents",
        "/Users/reneluijk/projects/thewaytowriteagents",
        "/Users/reneluijk/projects/uccli",
        "/Users/reneluijk/projects/metaprompt"
    ]
    search_string = "chatroom"
    file_extensions = ["json"]  # Adjust filters dynamically

    # Perform the search
    search_repos(repositories, search_string, file_extensions)
