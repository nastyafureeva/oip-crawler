import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



# Конфигурация краулера


@dataclass
class CrawlerConfig:
    """
    Хранит параметры запуска краулера.
    """
    base_url: str        # Шаблон URL (с {n})
    start_page: int      # Начальная страница
    end_page: int        # Конечная страница
    out_dir: str         # Папка для сохранения HTML
    index_path: str      # Путь к index.txt
    delay_sec: float     # Задержка между запросами
    timeout_sec: float   # Таймаут запроса
    user_agent: str      # Заголовок User-Agent



# Генерация списка URL


def build_urls(base_url: str, start_page: int, end_page: int) -> List[Tuple[int, str]]:
    """
    Генерирует список URL по шаблону.

    Пример:
    base_url = "https://site.com/p.{n}/index.html"

    Результат:
    [(1, "...p.1/index.html"), (2, "...p.2/index.html"), ...]
    """
    urls = []
    for n in range(start_page, end_page + 1):
        url = base_url.format(n=n)
        urls.append((n, url))
    return urls



# Создание HTTP-сессии

def make_session(user_agent: str) -> requests.Session:
    """
    Создает HTTP-сессию с:
    - заголовками
    - автоматическими retry
    """

    session = requests.Session()

    # Заголовки запроса (чтобы сервер воспринимал как обычный браузер)
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.8",
        "Connection": "keep-alive",
    })

    # Настройка повторных попыток при временных ошибках сервера
    retry = Retry(
        total=5,                 # максимум 5 повторов
        backoff_factor=0.8,      # задержка между повторами
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# Проверка что страница текстовая


def is_html_response(resp: requests.Response) -> bool:
    """
    Проверяет заголовок Content-Type.
    Нужны только текстовые страницы.
    """
    ctype = resp.headers.get("Content-Type", "").lower()

    return (
        "text/html" in ctype
        or "application/xhtml+xml" in ctype
        or ctype.startswith("text/")
    )



# Вспомогательные функции


def ensure_dir(path: str) -> None:
    """Создаёт папку, если её нет."""
    os.makedirs(path, exist_ok=True)


def file_name_for_index(i: int, total_digits: int = 4) -> str:
    """
    Формирует имя файла с ведущими нулями:
    1 -> 0001.html
    """
    return f"{i:0{total_digits}d}.html"



# Основная логика краулера

def crawl(config: CrawlerConfig) -> None:
    """
    Основная функция:
    - скачивает страницы
    - сохраняет HTML
    - формирует index.txt
    """

    ensure_dir(config.out_dir)

    session = make_session(config.user_agent)

    # Получаем список страниц
    targets = build_urls(config.base_url, config.start_page, config.end_page)
    total = len(targets)

    digits = max(4, len(str(total)))
    index_lines: List[str] = []

    print(f"Будет скачано страниц: {total}")
    print("Начинаем...\n")

    downloaded = 0

    for idx, (n, url) in enumerate(targets, start=1):

        fname = file_name_for_index(idx, total_digits=digits)
        out_path = os.path.join(config.out_dir, fname)

        # Если файл уже существует — пропускаем (можно докачивать)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(f"[{idx}/{total}] Уже скачан: {fname}")
            index_lines.append(f"{fname}\t{url}")
            downloaded += 1
            continue

        try:
            resp = session.get(url, timeout=config.timeout_sec)
        except requests.RequestException as e:
            print(f"[{idx}/{total}] Ошибка запроса: {url}")
            print(e)
            continue

        # Проверяем статус ответа
        if resp.status_code != 200:
            print(f"[{idx}/{total}] HTTP {resp.status_code}: {url}")
            continue

        # Проверяем, что это текстовая страница
        if not is_html_response(resp):
            print(f"[{idx}/{total}] Не текстовая страница: {url}")
            continue

        # Сохраняем HTML как есть (без очистки)
        html_text = resp.text

        with open(out_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(html_text)

        index_lines.append(f"{fname}\t{url}")
        downloaded += 1

        print(f"[{idx}/{total}] OK -> {fname}")

        # Пауза, чтобы не перегружать сервер
        time.sleep(config.delay_sec)

    # Записываем index.txt
    with open(config.index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines) + "\n")

    print("\nГотово.")
    print(f"Скачано: {downloaded}/{total}")

    if downloaded < total:
        print("Некоторые страницы не скачались. Можно запустить повторно.")
        sys.exit(2)



# Парсинг аргументов CLI


def parse_args() -> CrawlerConfig:
    """
    Позволяет запускать скрипт через параметры командной строки.
    """

    parser = argparse.ArgumentParser(
        description="HTML crawler for university task"
    )

    parser.add_argument(
        "--base-url",
        default="https://ilibrary.ru/text/1099/p.{n}/index.html",
        help="URL-шаблон с {n}",
    )

    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=100)
    parser.add_argument("--out-dir", default="dump")
    parser.add_argument("--index", default="index.txt")
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--timeout", type=float, default=20.0)

    parser.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (compatible; UniCrawler/1.0)",
    )

    args = parser.parse_args()

    return CrawlerConfig(
        base_url=args.base_url,
        start_page=args.start,
        end_page=args.end,
        out_dir=args.out_dir,
        index_path=args.index,
        delay_sec=args.delay,
        timeout_sec=args.timeout,
        user_agent=args.user_agent,
    )


# Точка входа

if __name__ == "__main__":
    config = parse_args()
    crawl(config)