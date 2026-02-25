# Deployment Manual

## Требования

- macOS / Linux / Windows
- Python 3.10+

Проверить версию Python:

```bash
python3 --version
```
Установка
1. Скачать репозиторий
```bash
git clone 
cd oip-crawler
```
2. (Рекомендуется) Создать виртуальное окружение
```bash
python3 -m venv .venv
source .venv/bin/activate
```
3. Установить зависимости
```bash
pip install -r requirements.txt
```
Запуск
```bash
python3 crawler.py --start 1 --end 100
```

## Что будет создано

После выполнения будут созданы:

папка dump/
100 HTML-файлов
файл index.txt

Повторный запуск

Если часть страниц не скачалась, можно запустить скрипт повторно:
```bash
python3 crawler.py --start 1 --end 100
```