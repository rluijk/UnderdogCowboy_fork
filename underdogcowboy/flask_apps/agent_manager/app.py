from underdogcowboy.flask_apps.agent_manager import create_app

def main():
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)

if __name__ == "__main__":
    main()
