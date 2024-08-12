# Loading our gitbookdoc agents that was saved from a dialog
# in our command line interface the timelineeditor. 
# The timelineeditor cli script is part of the underdodcowboy library:
# pip install underdogcowboy

from underdogcowboy import adm, gitbookdoc

    # Enable dialog with the agent via the Agent Dialog Manager (adm)
    adm | [gitbookdoc]

    # Ask the agent to make some documentation.
    # In this case about this script as we see here, since this will allow
    # it to have a small initial understanding and 
    # conversation about our small DSL as used in this script

    # The file reference to this script
    file_ref = "/Users/reneluijk/projects/UnderdogCowboy/examples/script_explorations/gitbookdocumenting.py"

    # Send the script to the agent (the LLM)
    response = gitbookdoc >> f"file {file_ref}"
    print(response)

# Put the Agent Dialog Manager interactive mode (+adm) to continue the conversation with the gitbookdoc agent
# in the command line interface (CLI).
+adm

# Users of the script can develop agents step by step, integrating 
# in larger and larger scripts.

