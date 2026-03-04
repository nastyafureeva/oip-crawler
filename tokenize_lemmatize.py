from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Set

from bs4 import BeautifulSoup
import pymorphy3

# Морфологический анализатор создаём один раз 
morph = pymorphy3.MorphAnalyzer(lang="ru")


# Русские стоп-слова (доп. фильтр; основной фильтр по частям речи ниже)
RU_STOPWORDS: Set[str] = {
    "и","в","во","на","по","к","ко","с","со","у","о","об","от","до","за","из","для","при","без","над","под","про","через","между",
    "а","но","или","либо","да","же","то","это","этот","эта","эти","этих","этой","этому","этим","этом","тут","там","здесь",
    "как","что","чего","чему","кто","кого","кому","который","которая","которое","которые","которых","которому","которыми",
    "я","мы","ты","вы","он","она","оно","они","мой","твой","ваш","наш","свой","его","её","их","ему","ей","им","ними","мне","меня","нам","нас","вам","вас",
    "не","ни","нет","бы","быть","будет","будут","был","была","были","есть",
    "так","уже","ещё","еще","только","всё","все","сейчас","тогда","потом","затем","тоже","также","очень","почти","лишь","просто","однако","поэтому","поскольку",
    "один","одна","одно","одни","два","две","три","четыре","пять","шесть","семь","восемь","девять","десять",
}

EN_STOPWORDS: Set[str] = {
    "the","a","an","and","or","but","of","to","in","on","for","with","as","at","by","from",
    "is","are","was","were","be","been","being","it","this","that","these","those",
}

# Части речи, которые нужно исключить:
# PREP — предлог, CONJ — союз, PRCL — частица, INTJ — междометие, NUMR — числительное
BAD_POS: Set[str] = {"PREP", "CONJ", "PRCL", "INTJ", "NUMR"}

# Ищем "похожие на слова" последовательности (только кириллица, допускаем дефис/апостроф)
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\-']+")


def html_to_text(html: str) -> str:
    """Преобразует HTML в обычный текст и убирает скрипты/стили."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def iter_html_files(dump_dir: Path) -> Iterable[Path]:
    """Возвращает все *.html файлы из каталога dump/."""
    for p in sorted(dump_dir.glob("*.html")):
        if p.is_file():
            yield p


def is_clean_token(raw: str) -> bool:
    """
    Фильтр "мусора":
    - никаких цифр (в т.ч. смешанных слов типа 'abc123')
    - только буквы + дефис/апостроф
    - минимум 2 буквы
    """
    if not raw:
        return False
    if any(ch.isdigit() for ch in raw):
        return False
    if re.search(r"[^A-Za-zА-Яа-яЁё\-']", raw):
        return False
    letters = [ch for ch in raw if ch.isalpha()]
    return len(letters) >= 2


def normalize_token(tok: str) -> str:
    """Нормализация токена: нижний регистр + ё→е."""
    return tok.lower().replace("ё", "е")


def is_stopword(tok_norm: str) -> bool:
    """Проверка по стоп-словам (дополнительно к POS-фильтру)."""
    return tok_norm in RU_STOPWORDS or tok_norm in EN_STOPWORDS


def reject_by_pos(tok_norm: str) -> bool:
    """
    Убираем союзы/предлоги/частицы/междометия/числительные по части речи.
    Применяем только к русским словам (для английских просто не фильтруем по POS).
    """
    if not re.search(r"[А-Яа-яЁё]", tok_norm):
        return False  # не русское слово -> не фильтруем по pymorphy

    p = morph.parse(tok_norm)[0]
    pos = p.tag.POS  # может быть None
    return (pos in BAD_POS)


def lemmatize(tok_norm: str) -> str:
    """Получаем лемму для русского слова."""
    if not re.search(r"[А-Яа-яЁё]", tok_norm):
        return tok_norm
    return morph.parse(tok_norm)[0].normal_form


def extract_tokens_from_html(html_path: Path) -> List[str]:
    """
    Извлекает токены из одной страницы:
    - чистка html -> текст
    - regex токенизация
    - фильтрация мусора/чисел/стоп-слов/предлогов/союзов
    - удаление дублей (в рамках данной страницы), порядок сохраняем
    """
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    text = html_to_text(html)

    seen: Set[str] = set()
    tokens: List[str] = []

    for raw in TOKEN_RE.findall(text):
        if not is_clean_token(raw):
            continue

        tok = normalize_token(raw)

        # стоп-слова
        if is_stopword(tok):
            continue

        # союзы/предлоги/числительные и т.п. по части речи
        if reject_by_pos(tok):
            continue

        # уникальность в пределах страницы
        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)

    return tokens


def group_tokens_by_lemmas(tokens: Iterable[str]) -> Dict[str, List[str]]:
    """
    Группировка токенов по леммам:
      лемма -> список форм (токенов)
    Дубликаты форм внутри леммы удаляем (порядок сохраняем).
    """
    lemma2tokens: Dict[str, List[str]] = {}

    for tok in tokens:
        lemma = lemmatize(tok)

        # на всякий случай ещё раз фильтруем стоп-леммы и "плохие" части речи
        if is_stopword(lemma):
            continue
        if reject_by_pos(lemma):
            continue

        lemma2tokens.setdefault(lemma, []).append(tok)

    # удаляем дубли форм внутри каждой леммы
    for lemma, forms in list(lemma2tokens.items()):
        dedup: List[str] = []
        seen: Set[str] = set()
        for f in forms:
            if f not in seen:
                seen.add(f)
                dedup.append(f)
        lemma2tokens[lemma] = dedup

    return lemma2tokens


def write_tokens(tokens: List[str], out_path: Path) -> None:
    """Записывает токены: <токен>\\n."""
    out_path.write_text("".join(t + "\n" for t in tokens), encoding="utf-8")


def write_lemmas(lemma2tokens: Dict[str, List[str]], out_path: Path) -> None:
    """Записывает леммы: <лемма> <токен1> <токен2> ...\\n."""
    lines: List[str] = []
    for lemma in sorted(lemma2tokens.keys()):
        lines.append(lemma + " " + " ".join(lemma2tokens[lemma]))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def safe_stem_name(p: Path) -> str:
    """
    Превращаем имя файла в базовое имя для вывода.
    Например: "001.html" -> "001"
    """
    return p.stem


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=Path("dump"), help="Каталог с HTML файлами")
    ap.add_argument("--out-dir", type=Path, default=Path("out"), help="Каталог для результатов (tokens/ и lemmas/)")
    args = ap.parse_args()

    dump_dir: Path = args.dump
    out_dir: Path = args.out_dir

    tokens_dir = out_dir / "tokens"
    lemmas_dir = out_dir / "lemmas"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    lemmas_dir.mkdir(parents=True, exist_ok=True)

    total_pages = 0
    total_tokens = 0
    total_lemmas = 0

    for html_path in iter_html_files(dump_dir):
        total_pages += 1

        # 1) токены для конкретной страницы
        page_tokens = extract_tokens_from_html(html_path)
        total_tokens += len(page_tokens)

        # 2) леммы для конкретной страницы
        page_lemma2tokens = group_tokens_by_lemmas(page_tokens)
        total_lemmas += len(page_lemma2tokens)

        name = safe_stem_name(html_path)

        # сохраняем в отдельные файлы
        write_tokens(page_tokens, tokens_dir / f"{name}.txt")
        write_lemmas(page_lemma2tokens, lemmas_dir / f"{name}.txt")

    print(f"Pages processed: {total_pages}")
    print(f"Total tokens (sum over pages): {total_tokens}")
    print(f"Total lemmas (sum over pages): {total_lemmas}")
    print(f"Output dir: {out_dir.resolve()}")


if __name__ == "__main__":
    main()