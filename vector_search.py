import os
import json
import math
import argparse
from collections import Counter
from typing import Dict, List, Set, Tuple

import pymorphy3


# Морфологический анализатор
morph = pymorphy3.MorphAnalyzer(lang="ru")


# Стоп-слова
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

BAD_POS: Set[str] = {"PREP", "CONJ", "PRCL", "INTJ", "NUMR"}


def normalize_token(tok: str) -> str:
    """Нижний регистр + ё -> е."""
    return tok.lower().replace("ё", "е")


def is_stopword(tok: str) -> bool:
    """Проверка стоп-слова."""
    return tok in RU_STOPWORDS or tok in EN_STOPWORDS


def reject_by_pos(tok: str) -> bool:
    """Отбрасываем служебные части речи."""
    if not any(("а" <= ch <= "я") or ("А" <= ch <= "Я") or ch in "ёЁ" for ch in tok):
        return False

    parsed = morph.parse(tok)[0]
    pos = parsed.tag.POS
    return pos in BAD_POS


def lemmatize(tok: str) -> str:
    """Лемматизация русского слова."""
    if not any(("а" <= ch <= "я") or ("А" <= ch <= "Я") or ch in "ёЁ" for ch in tok):
        return tok
    return morph.parse(tok)[0].normal_form


def process_query(query: str) -> List[str]:
    """
    Обработка запроса:
    - разбивка по пробелам
    - нормализация
    - удаление стоп-слов
    - POS-фильтр
    - лемматизация
    """
    raw_tokens = query.split()
    lemmas: List[str] = []

    for raw in raw_tokens:
        tok = normalize_token(raw.strip(".,!?;:()[]{}\"'"))
        if not tok:
            continue

        if is_stopword(tok):
            continue

        if reject_by_pos(tok):
            continue

        lemma = lemmatize(tok)

        if is_stopword(lemma):
            continue

        if reject_by_pos(lemma):
            continue

        lemmas.append(lemma)

    return lemmas


def load_index(path: str) -> Dict[str, Set[str]]:
    """Загрузка inverted_index.json."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return {term: set(docs) for term, docs in raw.items()}


def load_idf_from_any_doc(tfidf_dir: str) -> Dict[str, float]:
    """
    IDF берём из любого файла tfidf_lemmas.
    Формат строки: <лемма> <idf> <tf-idf>
    """
    files = sorted(f for f in os.listdir(tfidf_dir) if f.endswith(".txt"))
    if not files:
        raise RuntimeError(f"В каталоге {tfidf_dir} нет файлов .txt")

    sample_path = os.path.join(tfidf_dir, files[0])
    idf: Dict[str, float] = {}

    with open(sample_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            term = parts[0]
            idf_value = float(parts[1])
            idf[term] = idf_value

    return idf


def build_query_vector(query_terms: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    """TF-IDF вектор запроса."""
    counter = Counter(query_terms)
    total = len(query_terms)

    if total == 0:
        return {}

    qvec: Dict[str, float] = {}

    for term, count in counter.items():
        if term not in idf:
            continue
        tf = count / total
        qvec[term] = tf * idf[term]

    return qvec


def query_norm(vec: Dict[str, float]) -> float:
    """Норма вектора."""
    return math.sqrt(sum(w * w for w in vec.values()))


def read_doc_weights_and_norm(doc_path: str, needed_terms: Set[str]) -> Tuple[Dict[str, float], float]:
    """
    Читает один файл tfidf документа:
    - веса только для терминов запроса
    - полную норму документа
    """
    weights: Dict[str, float] = {}
    sq_sum = 0.0

    with open(doc_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 3:
                continue

            term = parts[0]
            tfidf = float(parts[2])

            sq_sum += tfidf * tfidf

            if term in needed_terms and tfidf != 0.0:
                weights[term] = tfidf

    return weights, math.sqrt(sq_sum)


def vector_search(
    query: str,
    index_path: str,
    tfidf_dir: str,
    top_k: int = 10,
) -> List[Tuple[str, float]]:
    """
    Векторный поиск:
    1) обрабатываем запрос
    2) через inverted index находим документы-кандидаты
    3) считаем cosine similarity только по ним
    """
    query_terms = process_query(query)
    if not query_terms:
        return []

    index = load_index(index_path)
    idf = load_idf_from_any_doc(tfidf_dir)

    qvec = build_query_vector(query_terms, idf)
    if not qvec:
        return []

    qnorm = query_norm(qvec)
    if qnorm == 0.0:
        return []

    needed_terms = set(qvec.keys())

    # Кандидаты: объединение списков документов по терминам запроса
    candidate_docs: Set[str] = set()
    for term in needed_terms:
        candidate_docs |= index.get(term, set())

    if not candidate_docs:
        return []

    scores: List[Tuple[str, float]] = []

    for doc_name in sorted(candidate_docs):
        doc_path = os.path.join(tfidf_dir, doc_name)

        if not os.path.exists(doc_path):
            continue

        doc_weights, dnorm = read_doc_weights_and_norm(doc_path, needed_terms)
        if dnorm == 0.0:
            continue

        dot = 0.0
        for term, qw in qvec.items():
            dot += qw * doc_weights.get(term, 0.0)

        score = dot / (qnorm * dnorm)
        if score > 0.0:
            scores.append((doc_name, score))

    scores.sort(key=lambda x: (-x[1], x[0]))
    return scores[:top_k]


def main():
    """CLI интерфейс."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Текст поискового запроса"
    )

    parser.add_argument(
        "--index",
        default="inverted_index.json",
        help="Путь к inverted_index.json"
    )

    parser.add_argument(
        "--tfidf-dir",
        default="tfidf_lemmas",
        help="Каталог с TF-IDF по леммам"
    )

    parser.add_argument(
        "--top", "-k",
        type=int,
        default=10,
        help="Сколько результатов вывести"
    )

    args = parser.parse_args()

    results = vector_search(
        query=args.query,
        index_path=args.index,
        tfidf_dir=args.tfidf_dir,
        top_k=args.top,
    )

    print(f"Query: {args.query}")
    print(f"Found: {len(results)}")

    for doc_name, score in results:
        print(f"{doc_name}\t{score:.6f}")


if __name__ == "__main__":
    main()