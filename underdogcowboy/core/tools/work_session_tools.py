

import os
from pathlib import Path
from datetime import datetime
import sys

def aggregate_files(directory_path, year="2024"):
    """
    Aggregates markdown and text files in the specified directory that start with the given year
    into two separate files.
    
    Parameters:
        directory_path (str or Path): Absolute path to the target directory.
        year (str): The year prefix for file selection (default is "2024").
        
    Returns:
        Tuple of Paths:
            - Path to the generated Markdown file
            - Path to the generated Text file
    """
    directory = Path(directory_path)

    if not directory.is_dir():
        print(f"Error: The path '{directory}' is not a valid directory.")
        return None, None

    # Get current date-time for postfix
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Get folder name
    folder_name = directory.name

    # Prepare output file names
    aggregate_md_filename = f"{folder_name}_{current_datetime}.md"
    aggregate_txt_filename = f"{folder_name}_{current_datetime}.txt"

    aggregate_md_path = directory / aggregate_md_filename
    aggregate_txt_path = directory / aggregate_txt_filename

    # Gather .md and .txt files that start with the specified year
    md_files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == '.md' and f.name.startswith(year)]
    txt_files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == '.txt' and f.name.startswith(year)]

    # Function to sort files by creation time descending
    def sort_by_ctime_desc(files):
        return sorted(files, key=lambda f: f.stat().st_ctime, reverse=True)

    md_files_sorted = sort_by_ctime_desc(md_files)
    txt_files_sorted = sort_by_ctime_desc(txt_files)

    # Aggregate Markdown files
    try:
        with aggregate_md_path.open('w', encoding='utf-8') as agg_md:
            for file in md_files_sorted:
                with file.open('r', encoding='utf-8') as f:
                    content = f.read()
                    agg_md.write(f"# {file.name}\n\n")
                    agg_md.write(content + "\n\n")
        print(f"Aggregated Markdown file created at: {aggregate_md_path}")
    except Exception as e:
        print(f"Error while aggregating Markdown files: {e}")

    # Aggregate Text files
    try:
        with aggregate_txt_path.open('w', encoding='utf-8') as agg_txt:
            for file in txt_files_sorted:
                with file.open('r', encoding='utf-8') as f:
                    content = f.read()
                    agg_txt.write(f"---\n# {file.name}\n---\n\n")
                    agg_txt.write(content + "\n\n")
        print(f"Aggregated Text file created at: {aggregate_txt_path}")
    except Exception as e:
        print(f"Error while aggregating Text files: {e}")

    # Return the paths to the generated files
    return aggregate_md_path, aggregate_txt_path
