import json
import os
import shutil
import subprocess
import time

import psutil
import redis
from celery import Celery
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from uvicorn import run

# FastAPI App Setup
app = FastAPI()

# Celery Configuration
celery = Celery(__name__)
celery.conf.broker_url = 'redis://localhost:6379/0'
celery.conf.result_backend = 'redis://localhost:6379/0'
celery.conf.imports = ['queue_runner']

celery.conf.worker_pool = 'solo'  # Use solo pool to avoid Windows-specific issues

# Redis Client Setup
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Paths
SCRIPTS_DIR = '/home'
TEMP_DIR = '/workspaces/full-stack-super-computer/temp'

os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


class ScriptRequest(BaseModel):
    folder_name: str


@app.post("/stop")
def stop_script():
    redis_client.set("paused", "True")
    return {"message": "Execution paused."}


@app.post("/resume")
def resume_execution():
    redis_client.set("paused", "False")
    return {"message": "Execution resumed."}


@celery.task(name='app.queue_runner.execute_script')
def execute_script(folder_name):
    while redis_client.get("paused") == b"True":
        print("Execution paused...")
        time.sleep(1)

    folder_path = os.path.abspath(os.path.join(SCRIPTS_DIR, folder_name))
    venv_path = os.path.join(folder_path, '.venv')
    python_executable = os.path.join(venv_path, 'bin', 'python')
    print(python_executable)

    if not os.path.exists(python_executable):
        raise FileNotFoundError(
            f"Python executable not found in virtual environment: {venv_path}")

    temp_env_dir = os.path.abspath(os.path.join(TEMP_DIR, folder_name))
    os.makedirs(temp_env_dir, exist_ok=True)

    running_containers = redis_client.get("running_containers")
    if running_containers:
        running_containers = json.loads(running_containers)
    else:
        running_containers = {}

    running_containers[folder_path] = {"folder_name": folder_name}
    redis_client.set("running_containers", json.dumps(running_containers))

    print(
        f"Container started for folder: {folder_name}. Waiting for it to finish...")

    try:
        script_path = os.path.join(folder_path, 'main.py')
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"main.py not found in {folder_path}")

        print(
            f"Executing script in folder: {folder_name} using its virtual environment")

        result = subprocess.run(
            [python_executable, script_path],
            cwd=folder_path,
            capture_output=True,
            text=True
        )

        print(
            f"Execution completed for {folder_name}. Output:\n{result.stdout}")

        if result.returncode != 0:
            print(f"Error executing script in {folder_name}: {result.stderr}")
            raise RuntimeError(f"Script execution failed: {result.stderr}")

    except Exception as e:
        print(f"Error executing script in {folder_name}: {e}")

    finally:
        print(f"Cleaning up temporary environment for folder: {folder_name}")
        shutil.rmtree(temp_env_dir, ignore_errors=True)


@app.post("/queue")
def queue_script(request: ScriptRequest):
    folder_name = request.folder_name
    folder_path = os.path.join(SCRIPTS_DIR, folder_name)

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder does not exist")

    print(f"Queuing task for folder: {folder_name}")
    try:
        task = execute_script.delay(folder_name)
        print(f"Task ID: {task.id}")
    except Exception as e:
        print(f"Error adding task: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue task")

    return {"message": f"Folder {folder_name} queued for execution"}


@app.post("/skip")
def skip_script():
    try:
        # Получение списка выполняемых скриптов из Redis
        running_scripts = redis_client.get("running_containers")
        if not running_scripts:
            raise HTTPException(
                status_code=404, detail="No running scripts to skip")

        running_scripts = json.loads(running_scripts)
        if not running_scripts:
            raise HTTPException(
                status_code=404, detail="No running scripts to skip")

        print("/////////////////////////////////////////////////////")
        print(running_scripts)
        print("/////////////////////////////////////////////////////")

        # Удаление текущего скрипта из очереди
        current_script_id = next(iter(running_scripts))
        command = os.path.join(current_script_id, 'main.py')
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                # Проверяем, соответствует ли командная строка

                print(proc.info)
                # print(proc.info['cmdline'])
                # print(' '.join(proc.info['cmdline']))
                # break
                if_none = proc.info['cmdline']

                if if_none is not None and command in ' '.join(proc.info['cmdline']):
                    pid = proc.info['pid']
                    print(f"Found process with PID {pid}. Killing it...")
                    os.kill(pid, 9)  # Отправляем сигнал SIGKILL
                    print(f"Process {pid} killed.")
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

        current_script_info = running_scripts.pop(current_script_id)
        redis_client.set("running_containers", json.dumps(running_scripts))

        # Уведомление об отмене выполнения текущего скрипта
        print(f"Skipping script execution: {current_script_id}")

        # Пометить выполнение как пропущенное
        redis_client.set(f"script_status:{current_script_id}", "skipped")

        return {"message": f"Script {current_script_id} skipped. Proceeding to next script."}

    except Exception as e:
        print(f"Error processing skip command: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to process skip command")


if __name__ == '__main__':
    run(app, host="0.0.0.0", port=8000)


a = {'1': {'folder_name': '1'},
     '/workspaces/full-stack-super-computer/user_folders/3': {'folder_name': '3'}
     }
