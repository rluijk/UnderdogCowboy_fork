import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from underdogcowboy.core import game_logic

def main():
    print("Welcome to UnderdogCowboy!")
    game_logic.start_game()

if __name__ == "__main__":
    main()