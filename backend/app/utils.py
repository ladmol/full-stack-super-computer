import logging
import subprocess
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails  # type: ignore
import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.config import settings
from app.models import Job


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logging.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


class JobQueueManager:
    def __init__(self):
        self.queue = deque()

    def load_jobs(self, db: SessionDep):
        """
        Загружает задачи из базы данных в очередь.
        """
        statement = select(Job).where(
            Job.owner_id.isnot(None)).order_by(Job.id)
        results = db.exec(statement).all()

        for job in results:
            self.queue.append(job[0])  # job[0] - объект Job из кортежа
        print(f"Загружено {len(self.queue)} задач в очередь.")

    def add_job(self, db: SessionDep, job: Job):
        """
        Добавляет задачу в базу данных и очередь.
        """
        db.add(job)
        db.commit()
        db.refresh(job)
        self.queue.append(job)
        print(f"Задача {job.title} добавлена в очередь.")

    def get_next_job(self) -> Job | None:
        """
        Получает следующую задачу из очереди.
        """
        if self.queue:
            return self.queue.popleft()
        print("Очередь пуста.")
        return None

    def process_job(self, job: Job):
        """
        Обрабатывает задачу (например, выполнение Python-скрипта).
        """
        print(f"Обработка задачи '{job.title}': {job.description}")
        try:
            subprocess.run(["python", job.description], check=True)
            print(f"Задача '{job.title}' успешно выполнена.")
        except subprocess.CalledProcessError:
            print(f"Ошибка при выполнении задачи '{job.title}'.")

    def remove_job(self, db: SessionDep, job: Job):
        """
        Удаляет задачу из базы данных после выполнения.
        """
        db.delete(job)
        db.commit()
        print(f"Задача '{job.title}' удалена из очереди.")
