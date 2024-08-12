import json
import os
import shutil

def extract_and_copy_files(tour_json_path, output_folder="codetour_files"):
    """
    Extracts file references from a CodeTour JSON file and copies those files,
    along with the JSON itself, into a specified output folder.

    Args:
        tour_json_path (str): Path to the CodeTour JSON file.
        output_folder (str, optional): Name of the output folder. Defaults to "codetour_files".
    """

    try:
        with open(tour_json_path, "r") as f:
            tour_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {tour_json_path}")
        return

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Copy the CodeTour JSON file
    shutil.copy(tour_json_path, output_folder)

    # Extract and copy referenced files
    for step in tour_data.get("steps", []):
        file_path = step.get("file")
        if file_path:
            try:
                shutil.copy(file_path, output_folder)
                print(f"Copied: {file_path} to {output_folder}")
            except FileNotFoundError:
                print(f"Warning: File not found: {file_path}")

    print(f"Files copied to: {output_folder}")

if __name__ == "__main__":
    tour_json_path = "/Users/reneluijk/projects/UnderdogCowboy/.tours/making-an-agent-in-package.tour"
    extract_and_copy_files(tour_json_path)