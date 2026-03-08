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

## Токенизация и лемматизация

После скачивания страниц можно выполнить обработку текста.

```bash
python3 tokenize_lemmatize.py --dump dump --out-dir out
```
Будут созданы файлы:

out/
  tokens/
    *.txt
  lemmas/
    *.txt

Для каждой страницы:

файл со списком токенов
файл с леммами и соответствующими токенами



## Построение инвертированного индекса

После лемматизации можно построить инвертированный индекс:

```bash
python3 build_index_from_lemmas.py --lemmas out/lemmas --out inverted_index.json
```
Будет создан файл:

inverted_index.json

## Булев поиск

Поиск выполняется по построенному индексу.

Пример:

```bash
python3 boolean_search.py -q "(клеопатра AND цезарь) OR помпей"
```
На экран выводится список документов, удовлетворяющих запросу.

## Расчет TF-IDF

После токенизации и лемматизации можно выполнить расчет TF-IDF.

```bash
python3 tfidf.py
```
Будут созданы файлы:

tfidf_tokens/
*.txt

tfidf_lemmas/
*.txt

Каждый файл соответствует одному документу.

## Векторный поиск

После построения TF-IDF можно выполнять поиск по документам
с использованием векторной модели.

```bash
python3 vector_search.py -q "семья счастливая" --top 10
```
Пример вывода

Query: семья счастливая
Found: 10
0001.txt        0.054121
0016.txt        0.050040
0019.txt        0.044159
0060.txt        0.042704
...