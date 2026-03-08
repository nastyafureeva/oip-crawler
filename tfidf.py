import os
import math
from collections import Counter, defaultdict


TOKENS_DIR = "out/tokens"   # по документам: токен на строку
LEMMAS_DIR = "out/lemmas"   # по документам: "лемма словоформа" на строку

OUT_TFIDF_TOKENS = "tfidf_tokens"
OUT_TFIDF_LEMMAS = "tfidf_lemmas"


def read_tokens_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def read_lemma_map_file(path: str) -> dict[str, set[str]]:
    """
    Вход: строки вида "<лемма> <словоформа>".
    Выход: lemma -> set(forms)
    """
    lemma2forms: dict[str, set[str]] = defaultdict(set)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                # если вдруг попалась строка только с леммой — считаем, что форма = лемма
                lemma = parts[0]
                lemma2forms[lemma].add(lemma)
                continue

            lemma, form = parts[0], parts[1]
            lemma2forms[lemma].add(form)

    return lemma2forms


def list_docs(folder: str) -> list[str]:
    return sorted([name for name in os.listdir(folder) if not name.startswith(".")])


def compute_df_terms(token_docs: list[list[str]]) -> dict[str, int]:
    """
    df(term) по токенам: сколько документов содержат term.
    """
    df: dict[str, int] = defaultdict(int)
    for tokens in token_docs:
        for term in set(tokens):
            df[term] += 1
    return df


def compute_df_lemmas(lemma_maps: list[dict[str, set[str]]]) -> dict[str, int]:
    """
    df(lemma) по леммам: сколько документов содержат lemma (есть хотя бы одна строка с этой леммой).
    """
    df: dict[str, int] = defaultdict(int)
    for lm in lemma_maps:
        for lemma in lm.keys():
            df[lemma] += 1
    return df


def idf_from_df(df: dict[str, int], N: int) -> dict[str, float]:
    # если df==0 не бывает (мы считаем только существующие ключи), но на всякий случай:
    return {k: (math.log(N / v) if v else 0.0) for k, v in df.items()}


def save_tfidf_terms(doc_names: list[str], token_docs: list[list[str]], idf: dict[str, float]) -> None:
    os.makedirs(OUT_TFIDF_TOKENS, exist_ok=True)

    vocab = sorted(idf.keys())

    for name, tokens in zip(doc_names, token_docs):
        counter = Counter(tokens)
        total = len(tokens)

        out_path = os.path.join(OUT_TFIDF_TOKENS, name)
        with open(out_path, "w", encoding="utf-8") as out:
            for term in vocab:
                tf = (counter[term] / total) if total else 0.0
                tfidf = tf * idf[term]
                out.write(f"{term} {idf[term]} {tfidf}\n")


def save_tfidf_lemmas(
    doc_names: list[str],
    token_docs: list[list[str]],
    lemma_maps: list[dict[str, set[str]]],
    idf: dict[str, float],
) -> None:
    """
    TF(lemma, d) = sum_{form in forms(lemma)} count(form, d) / |d|
    где |d| — общее число токенов документа (берём из out/tokens/<doc>.txt)
    """
    os.makedirs(OUT_TFIDF_LEMMAS, exist_ok=True)

    vocab = sorted(idf.keys())

    for name, tokens, lemma2forms in zip(doc_names, token_docs, lemma_maps):
        counter = Counter(tokens)
        total = len(tokens)

        out_path = os.path.join(OUT_TFIDF_LEMMAS, name)
        with open(out_path, "w", encoding="utf-8") as out:
            for lemma in vocab:
                forms = lemma2forms.get(lemma, set())
                # если в этом документе лемма не встречалась (нет строк в out/lemmas/<doc>.txt),
                # то tf = 0
                if not forms or not total:
                    tf = 0.0
                else:
                    tf = sum(counter[f] for f in forms) / total

                tfidf = tf * idf[lemma]
                # вывод  "<лемма> <idf> <tf-idf>"
                out.write(f"{lemma} {idf[lemma]} {tfidf}\n")


def main():
    # 1) Список файлов документов (ожидаем одинаковые имена в tokens/ и lemmas/)
    token_files = list_docs(TOKENS_DIR)
    lemma_files = list_docs(LEMMAS_DIR)

    if token_files != lemma_files:
        # если имена отличаются - лучше сразу упасть, чтобы не перепутать документы
        missing_in_lemmas = [f for f in token_files if f not in lemma_files]
        missing_in_tokens = [f for f in lemma_files if f not in token_files]
        raise RuntimeError(
            "Файлы в out/tokens и out/lemmas не совпадают.\n"
            f"Нет в out/lemmas: {missing_in_lemmas}\n"
            f"Нет в out/tokens: {missing_in_tokens}\n"
        )

    doc_names = token_files

    # 2) Читаем токены и леммы по документам
    token_docs: list[list[str]] = []
    lemma_maps: list[dict[str, set[str]]] = []

    for name in doc_names:
        token_docs.append(read_tokens_file(os.path.join(TOKENS_DIR, name)))
        lemma_maps.append(read_lemma_map_file(os.path.join(LEMMAS_DIR, name)))

    N = len(doc_names)

    # 3) DF/IDF
    df_terms = compute_df_terms(token_docs)
    df_lemmas = compute_df_lemmas(lemma_maps)

    idf_terms = idf_from_df(df_terms, N)
    idf_lemmas = idf_from_df(df_lemmas, N)

    # 4) Сохраняем tf-idf
    save_tfidf_terms(doc_names, token_docs, idf_terms)
    save_tfidf_lemmas(doc_names, token_docs, lemma_maps, idf_lemmas)


if __name__ == "__main__":
    main()