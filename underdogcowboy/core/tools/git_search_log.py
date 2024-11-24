#!/usr/bin/env python3

import subprocess
import os
import argparse
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitCommitInfo:
    """Store information about a git commit and its changes"""
    def __init__(self, commit_hash: str, author: str, date: str, 
                 file_path: str, content: str, full_hash: str):
        self.commit_hash = commit_hash
        self.author = author
        self.date = date
        self.file_path = file_path
        self.content = content
        self.full_hash = full_hash
        self.context_before: List[str] = []
        self.context_after: List[str] = []

def get_commit_details(repo_path: str, commit_hash: str) -> Tuple[str, str, str]:
    """Get author and date for a commit"""
    try:
        # Get full hash
        result = subprocess.run(
            ['git', 'rev-parse', commit_hash],
            capture_output=True, text=True, cwd=repo_path
        )
        full_hash = result.stdout.strip()

        # Get author and date
        result = subprocess.run(
            ['git', 'show', '-s', '--format=%an|%ai', commit_hash],
            capture_output=True, text=True, cwd=repo_path
        )
        author, date = result.stdout.strip().split('|')
        return full_hash, author, date
    except Exception as e:
        logger.error(f"Error getting commit details: {e}")
        return commit_hash, "Unknown", "Unknown"

def parse_git_log_output(output: str, repo_path: str) -> List[GitCommitInfo]:
    """Parse git log -p output into structured format"""
    commits = []
    current_commit = None
    current_file = None
    content_buffer = []
    
    try:
        lines = output.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.startswith('commit '):
                if current_commit and content_buffer:
                    # Process previous commit
                    full_hash, author, date = get_commit_details(repo_path, current_commit)
                    commits.append(GitCommitInfo(
                        current_commit,
                        author,
                        date,
                        current_file,
                        '\n'.join(content_buffer),
                        full_hash
                    ))
                    content_buffer = []
                
                current_commit = line.split()[1]
                
            elif line.startswith('diff --git '):
                current_file = line.split(' b/')[1]
                
            elif line.startswith('@@'):
                # Collect context lines
                content_buffer = []
                i += 1
                while i < len(lines) and not (lines[i].startswith('diff ') or 
                                            lines[i].startswith('commit ')):
                    if lines[i].startswith('+'):
                        content_buffer.append(lines[i][1:])
                    i += 1
                continue
                
            i += 1
            
        # Process last commit
        if current_commit and content_buffer:
            full_hash, author, date = get_commit_details(repo_path, current_commit)
            commits.append(GitCommitInfo(
                current_commit,
                author,
                date,
                current_file,
                '\n'.join(content_buffer),
                full_hash
            ))
    
    except Exception as e:
        logger.error(f"Error parsing git log output: {e}")
    
    return commits

def search_repos(repos: List[str], search_term: str, 
                file_filters: List[str]) -> Dict[str, List[GitCommitInfo]]:
    """Search for when a term was added or modified in specified git repositories"""
    all_results = {}
    
    for repo in repos:
        try:
            logger.info(f"Searching in repository: {repo}")
            
            # Change to the repo directory
            os.chdir(repo)

            # Construct the git log command
            file_pattern = " ".join([f"'*.{ext}'" for ext in file_filters])
            command = f"""git log -p -G'{search_term}' --all -- {file_pattern}"""

            # Execute the command and capture the output
            result = subprocess.run(command, shell=True, text=True, capture_output=True)

            if result.stdout:
                matches = parse_git_log_output(result.stdout, repo)
                if matches:
                    all_results[repo] = matches
                    logger.info(f"Found {len(matches)} matches in {repo}")

        except Exception as e:
            logger.error(f"Failed to search in {repo}: {e}")

    return all_results

def format_results_as_markdown(results: Dict[str, List[GitCommitInfo]], 
                             search_term: str) -> str:
    """Format search results as proper markdown table"""
    markdown = []
    
    # Table header
    header = ("| Repository | File | Change Context | Commit | Author | Date | "
             "Repository Path | Git Command |")
    separator = ("|------------|------|---------------|--------|--------|------|"
                "----------------|-------------|")
    
    markdown.append(header)
    markdown.append(separator)
    
    # Table rows
    for repo, commits in results.items():
        repo_name = os.path.basename(repo)
        for commit in commits:
            # Clean up and truncate content
            context = commit.content.replace('\n', ' ').replace('|', '\\|')
            if len(context) > 100:
                context = context[:97] + "..."
            
            # Format date
            try:
                date = datetime.strptime(commit.date.split()[0], '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                date = commit.date
            
            # Create git command
            git_command = f"cd {repo} && git show {commit.full_hash}:{commit.file_path}"
            
            # Create row
            row = (f"| {repo_name} | {commit.file_path} | {context} | "
                  f"{commit.commit_hash[:7]} | {commit.author} | {date} | "
                  f"{repo} | `{git_command}` |")
            markdown.append(row)
    
    return "\n".join(markdown)

def save_search_results(markdown_results: str, search_term: str) -> None:
    """Save search results to a markdown file in ~/.uc_search directory"""
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

    logger.info(f"Search results saved to: file://{os.path.abspath(filepath)}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Search git repositories for content addition/modification history',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "search term"
  %(prog)s "search term" -f json md py
  %(prog)s "search term" --filters json md py --verbose
        """
    )
    
    parser.add_argument('search_term', 
                       help='The string to search for in the repositories')
    parser.add_argument('-f', '--filters', 
                       nargs='+', 
                       default=['json', 'md', 'py'],
                       help='File extensions to search in (default: json md py)')
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='Increase output verbosity')

    # Parse arguments
    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

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

    # Perform the search
    logger.info(f"Searching for: {args.search_term}")
    logger.info(f"File filters: {args.filters}")
    
    results = search_repos(repositories, args.search_term, args.filters)
    
    if results:
        markdown_results = format_results_as_markdown(results, args.search_term)
        save_search_results(markdown_results, args.search_term)
    else:
        logger.info("No results found.")

if __name__ == "__main__":
    main()