import subprocess
import os
from datetime import datetime
import argparse


def format_results_as_markdown(results):
    """
    Format search results as proper markdown table with git commands
    """
    markdown = []
    
    # Table header with proper cell alignment
    header = "| Repository | File | Match Preview | Commit | Repository Path | Git Command |"
    separator = "|------------|------|--------------|---------|----------------|-------------|"
    
    markdown.append(header)
    markdown.append(separator)
    
    # Table rows
    for repo, matches in results.items():
        repo_name = os.path.basename(repo)
        for match in matches:
            # Clean up the match content
            match_content = match['match'].replace('\n', ' ').strip()
            if len(match_content) > 100:
                match_content = match_content[:97] + "..."
            
            # Escape any pipe characters in the content
            match_content = match_content.replace("|", "\\|")
            file_path = match['file'].replace("|", "\\|")
            
            # Create git command
            git_command = f"cd {repo} && git show {match['commit']}:{file_path}"
            # Alternative command to open the file at that commit:
            # git_command = f"cd {repo} && git checkout {match['commit']} && git show {match['commit']}:{file_path}"
            
            # Create properly formatted table row
            row = f"| {repo_name} | {file_path} | {match_content} | {match['commit'][:7]} | {repo} | `{git_command}` |"
            markdown.append(row)
    
    return "\n".join(markdown)

def parse_git_grep_output(output, repo):
    """
    Parse git grep output into structured format.
    
    :param output: String output from git grep
    :param repo: Repository path
    :return: List of dictionaries containing match information
    """
    matches = []
    for line in output.strip().split('\n'):
        if line:
            try:
                commit, file_match = line.split(':', 1)
                file_path, match_content = file_match.split(':', 1)
                matches.append({
                    'commit': commit.strip(),
                    'file': file_path.strip(),
                    'match': match_content.strip()
                })
            except ValueError:
                continue
    return matches

def search_repos(repos, search_term, file_filters):
    """
    Search for a term in specified git repositories with dynamic file filters.

    :param repos: List of repository paths
    :param search_term: Term to search for
    :param file_filters: List of file extensions to filter (e.g., ['json', 'py'])
    :return: Markdown formatted table of results
    """
    all_results = {}
    
    for repo in repos:
        try:
            # Change to the repo directory
            os.chdir(repo)

            # Construct the git grep command
            filters = " ".join([f"'*.{ext}'" for ext in file_filters])
            command = f"git grep -F '{search_term}' $(git rev-list --all) -- {filters}"

            # Execute the command and capture the output
            result = subprocess.run(command, shell=True, text=True, capture_output=True)

            if result.stdout:
                matches = parse_git_grep_output(result.stdout, repo)
                if matches:
                    all_results[repo] = matches

        except Exception as e:
            print(f"Failed to search in {repo}: {e}")

    # Generate markdown table
    markdown_table = format_results_as_markdown(all_results)
    return markdown_table



def save_search_results(markdown_results, search_term):
    """
    Save search results to a markdown file in ~/.uc_search directory
    """
    # Create search directory in user's home
    search_dir = os.path.expanduser("~/.uc_search")
    os.makedirs(search_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_{search_term}_{timestamp}.md"
    filepath = os.path.join(search_dir, filename)

    # Write results to file
    with open(filepath, 'w') as f:
        f.write(f"# Search Results for '{search_term}'\n\n")
        f.write(f"Search performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(markdown_results)

    print(f"\nSearch results saved to: {filepath}")
    print(f"\nSearch results saved to: file://{os.path.abspath(filepath)}")




if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Search through git repositories')
    parser.add_argument('search_string', 
                      help='The string to search for in the repositories')
    parser.add_argument('-f', '--filters', 
                      nargs='+', 
                      default=['json', 'md', 'py'],
                      help='File extensions to search in (default: json md py)')

    # Parse arguments
    args = parser.parse_args()

    # Define repositories
    repositories = [
        "/Users/reneluijk/llm_dialogs",
        "/Users/reneluijk/projects/UnderdogCowboy",
        "/Users/reneluijk/obsidian_vaults/workshop/workshop-materials",
        "/users/reneluijk/.underdogcowboy/agents",
        "/Users/reneluijk/projects/thewaytowriteagents",
        "/Users/reneluijk/projects/uccli",
        "/Users/reneluijk/projects/metaprompt"
    ]

    # Perform the search and get markdown table
    markdown_results = search_repos(repositories, args.search_string, args.filters)
    
    # Save or report results
    if markdown_results:
        save_search_results(markdown_results, args.search_string)
    else:
        print("\nNo results found to save.")
