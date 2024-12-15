#!/bin/bash

# Agent Manager
echo "Building Agent Manager React app..."
cd ../apps/ui_agent_manager || exit
npm run build || exit
echo "Copying build to Flask app..."
cp -r build/* ../../underdogcowboy/flask_apps/agent_manager/react_ui/

echo "All builds complete!"
