# oip-crawler  
Фуреева Анастасия Денисовна 11-202 гр

## Описание

Краулер скачивает 100 HTML-страниц с сайта https://ilibrary.ru  
Страницы сохраняются вместе с HTML-разметкой (без очистки).

Для каждой страницы создаётся отдельный файл в папке `dump/`.

Также создаётся файл `index.txt`, содержащий соответствие:

имя_файла -> ссылка_на_страницу

## Используемые технологии

- Python 3.13
- requests

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 crawler.py --start 1 --end 100