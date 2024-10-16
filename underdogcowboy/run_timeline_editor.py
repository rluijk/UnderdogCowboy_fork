import os
import sys

# Add the parent directory of 'underdogcowboy' to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from underdogcowboy.core.timeline_editor import main

if __name__ == "__main__":
    main()