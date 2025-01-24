import os
import subprocess
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Константы
USERNAME = "edgerunner"
GROUP = "video"
HOME_PATH = "/home"


def user_exists(username):
    """Проверяет, существует ли пользователь."""
    result = subprocess.run(["id", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def create_user(username):
    """Создает пользователя."""
    try:
        subprocess.run(["sudo", "useradd", "-s", "/bin/bash", username], check=True)
        logging.info(f"Пользователь {username} успешно создан.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при создании пользователя {username}: {e}")


def user_in_group(username, group):
    """Проверяет, состоит ли пользователь в указанной группе."""
    try:
        result = subprocess.run(["groups", username], capture_output=True, text=True, check=True)
        return group in result.stdout.split()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при проверке группы для {username}: {e}")


def add_user_to_group(username, group):
    """Добавляет пользователя в группу."""
    try:
        subprocess.run(["sudo", "usermod", "-aG", group, username], check=True)
        logging.info(f"Пользователь {username} добавлен в группу {group}.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при добавлении {username} в группу {group}: {e}")


def setup_edgerunner(username, group):
    """Настраивает пользователя edgerunner и добавляет его в группу."""
    try:
        if not user_exists(username):
            create_user(username)
        else:
            logging.info(f"Пользователь {username} уже существует.")

        if not user_in_group(username, group):
            add_user_to_group(username, group)
        else:
            logging.info(f"Пользователь {username} уже состоит в группе {group}.")
    except RuntimeError as e:
        logging.error(e)


def grant_permissions(path, username):
    """Устанавливает права на папку для пользователя."""
    try:
        if not os.path.exists(path):
            logging.warning(f"Директория {path} не существует.")
            return

        subprocess.run(["sudo", "chmod", "-R", "u+rwx", path], check=True)
        logging.info(f"Права R/W/X для {username} установлены на {path}.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при установке прав на {path}: {e}")


def main():
    setup_edgerunner(USERNAME, GROUP)
    grant_permissions(HOME_PATH, USERNAME)


if __name__ == "__main__":
    main()
