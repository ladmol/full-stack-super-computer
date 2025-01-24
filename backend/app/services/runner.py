import os
import subprocess


def setup_edgerunner():
    username = "edgerunner"
    group = "video"

    try:
        # Проверяем, существует ли пользователь
        result = subprocess.run(
            ["id", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if result.returncode != 0:
            # Создаем пользователя и домашнюю директорию
            subprocess.run(["sudo", "useradd", "-s", "/bin/bash", username], check=True)
            print(f"Пользователь {username} успешно создан.")
        else:
            print(f"Пользователь {username} уже существует.")

        # Проверяем, состоит ли пользователь в группе video
        result = subprocess.run(["groups", username], capture_output=True, text=True)
        groups = result.stdout

        if group in groups:
            print(f"Пользователь {username} уже состоит в группе {group}.")
        else:
            # Добавляем пользователя в группу video
            subprocess.run(["sudo", "usermod", "-aG", group, username], check=True)
            print(f"Пользователь {username} добавлен в группу {group}.")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


def grant_home_permissions():
    edgerunner = "edgerunner"
    home_path = "/home"

    try:
        # Проверяем, существует ли директория /home
        if not os.path.exists(home_path):
            print(f"Директория {home_path} не существует.")
            return

        # Даём права edgerunner на папку /home и все папки внутри
        subprocess.run(["sudo", "chmod", "-R", "u+rwx", home_path], check=True)
        print(
            f"Права read/write/execute для {edgerunner} установлены на {home_path} и все вложенные папки."
        )

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


def main():
    setup_edgerunner()
    grant_home_permissions()


if __name__ == "__main__":
    main()
