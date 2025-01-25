import json
import os

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.celery_config import execute_script, redis_client

router = APIRouter()
class ScriptRequest(BaseModel):
    folder_name: str

# Paths
SCRIPTS_DIR = '/home'

@router.post("/pause")
def stop_script():
    redis_client.set("paused", "True")
    return {"message": "Execution paused."}


@router.post("/resume")
def resume_execution():
    redis_client.set("paused", "False")
    return {"message": "Execution resumed."}

# @router.post("/queue")
# def queue_script(request: ScriptRequest):
#     folder_name = request.folder_name
#     folder_path = os.path.join(SCRIPTS_DIR, folder_name)

#     if not os.path.exists(folder_path):
#         raise HTTPException(status_code=404, detail="Folder does not exist")

#     print(f"Queuing task for folder: {folder_name}")
#     try:
#         task = execute_script.delay(folder_name)
#         print(f"Task ID: {task.id}")
#     except Exception as e:
#         print(f"Error adding task: {e}")
#         raise HTTPException(status_code=500, detail="Failed to queue task")

#     return {"message": f"Folder {folder_name} queued for execution"}


@router.post("/skip")
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
