import subprocess

_APP_COMMANDS = {
    "chrome": ["cmd", "/c", "start", "", "chrome"],
    "vscode": ["cmd", "/c", "code"],
    "code": ["cmd", "/c", "code"],
    "explorer": ["explorer"],
    "file explorer": ["explorer"],
    "notepad": ["notepad"],
}


def open_app(app_name: str) -> str:
    key = (app_name or "").strip().lower()
    command = _APP_COMMANDS.get(key)
    if command is None:
        return f"I don't know how to open '{app_name}' yet."

    subprocess.Popen(command, shell=False)
    return f"Opening {app_name}."


def open_path_in_vscode(path: str) -> str:
    subprocess.Popen(["cmd", "/c", "code", path], shell=False)
    return f"Opening {path} in VS Code."
