import subprocess
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def check_user_exists(username):
    """
    Проверяет, существует ли пользователь.
    """
    result = subprocess.run(["id", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def create_system_user(username):
    """
    Создает пользователя в системе.
    """
    try:
        subprocess.run(["sudo", "useradd", "-m", "-s", "/bin/bash", username], check=True)
        logging.info(f"Пользователь {username} создан.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при создании пользователя {username}: {e}")


def set_user_password(username, password):
    """
    Устанавливает пароль для пользователя.
    """
    try:
        subprocess.run(["sudo", "chpasswd"], input=f"{username}:{password}".encode(), check=True)
        logging.info(f"Пароль для пользователя {username} установлен.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при установке пароля для {username}: {e}")


def setup_home_directory(username):
    """
    Настраивает домашнюю директорию пользователя.
    """
    home_dir = f"/home/{username}"
    try:
        subprocess.run(["sudo", "chmod", "700", home_dir], check=True)
        subprocess.run(["sudo", "chown", "-R", f"{username}:{username}", home_dir], check=True)
        logging.info(f"Домашняя директория {home_dir} настроена.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при настройке директории {home_dir}: {e}")


def create_user(username, password):
    """
    Главная функция для создания пользователя.
    """
    try:
        if check_user_exists(username):
            logging.warning(f"Пользователь {username} уже существует.")
            return

        create_system_user(username)
        set_user_password(username, password)
        setup_home_directory(username)

        logging.info(f"Пользователь {username} успешно создан.")
    except RuntimeError as e:
        logging.error(e)
    except Exception as e:
        logging.exception(f"Неизвестная ошибка: {e}")


def main():
    create_user("testuser", "testpassword")


if __name__ == "__main__":
    main()
