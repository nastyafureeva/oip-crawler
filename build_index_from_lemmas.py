import os
import json
import argparse
from typing import Dict, Set


# Чтение лемм документа

def read_doc_lemmas(path: str) -> Set[str]:
    """
    Читает файл документа и возвращает множество лемм.
    """

    lemmas: Set[str] = set()

    with open(path, "r", encoding="utf-8", errors="ignore") as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if not parts:
                continue

            # первая колонка — лемма
            lemmas.add(parts[0].lower())
            

    return lemmas


# Построение инвертированного индекса

def build_inverted_index(lemmas_dir: str) -> Dict[str, Set[str]]:
    """
    Формирует инвертированный индекс:
    lemma -> список документов
    """

    index: Dict[str, Set[str]] = {}

    for fname in sorted(os.listdir(lemmas_dir)):

        if not fname.endswith(".txt"):
            continue

        doc_id = fname

        doc_lemmas = read_doc_lemmas(
            os.path.join(lemmas_dir, fname)
        )

        for lm in doc_lemmas:
            index.setdefault(lm, set()).add(doc_id)

    return index


# Сохранение индекса

def save_index(index: Dict[str, Set[str]], out_path: str):
    """
    Сохраняет индекс в JSON файл.
    """

    data = {
        term: sorted(list(docs))
        for term, docs in index.items()
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Точка входа

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--lemmas", default="out/lemmas")
    parser.add_argument("--out", default="inverted_index.json")

    args = parser.parse_args()

    index = build_inverted_index(args.lemmas)

    save_index(index, args.out)

    print("terms:", len(index))
    print("saved:", args.out)


if __name__ == "__main__":
    main()