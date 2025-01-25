import json
import os
import shutil
import subprocess
import time

import redis
from celery import Celery

# Celery Configuration
celery = Celery(__name__)
celery.conf.broker_url = 'redis://localhost:6379/0'
celery.conf.result_backend = 'redis://localhost:6379/0'
# celery.conf.imports = ['celery_config.py']

celery.conf.worker_pool = 'solo'  # Use solo pool to avoid Windows-specific issues

# Redis Client Setup
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Paths
SCRIPTS_DIR = '/home'


@celery.task(name='app.core.celery_config.execute_script')
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
            print(
                f"Error executing script in {folder_name}: {result.stderr}")
            raise RuntimeError(f"Script execution failed: {result.stderr}")

    except Exception as e:
        print(f"Error executing script in {folder_name}: {e}")
