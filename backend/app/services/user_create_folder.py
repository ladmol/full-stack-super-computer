import subprocess


def create_user(username, password):
    try:
        # Проверяем, существует ли пользователь
        result = subprocess.run(
            ["id", username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if result.returncode == 0:
            print(f"Пользователь {username} уже существует.")
            return

        # Создаем пользователя и домашнюю директорию
        subprocess.run(
            ["sudo", "useradd", "-m", "-s", "/bin/bash", username], check=True
        )

        # Устанавливаем пароль пользователя
        subprocess.run(
            ["sudo", "chpasswd"], input=f"{username}:{password}".encode(), check=True
        )

        # Путь к домашней директории
        home_dir = f"/home/{username}"

        # Устанавливаем права на домашнюю директорию
        subprocess.run(["sudo", "chmod", "700", home_dir], check=True)
        subprocess.run(
            ["sudo", "chown", "-R", f"{username}:{username}", home_dir], check=True
        )

        print(
            f"Пользователь {username} успешно создан. Домашняя директория: {home_dir}"
        )

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


# Пример использования


def main():
    create_user("testuser", "testpassword")


if __name__ == "main":
    main()
