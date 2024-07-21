import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from underdogcowboy.core.timeline_editor import main as timeline_editor_main

def main():
    timeline_editor_main()

if __name__ == "__main__":
    main()    