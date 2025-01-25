#!/workspaces/full-stack-super-computer/backend/.venv/bin/python3
from typing import Annotated

import typer

from app.queue_runner import execute_script


def add(folder_name: Annotated[str, typer.Argument()]):
    try:
        task = execute_script.delay(folder_name)
        print(f"Task ID: {task.id}")
    except Exception as e:
        print(f"Error adding task: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(add)
