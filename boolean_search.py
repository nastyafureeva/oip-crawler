import json
import re
import argparse
from typing import Dict, Set, List


# Конфигурация булевого поиска

# Регулярное выражение для разбора запроса:
# слова (русские буквы и цифры), операторы AND/OR/NOT и скобки
TOKEN_RE = re.compile(r"\(|\)|AND|OR|NOT|[А-Яа-яЁё0-9]+", re.UNICODE)

# Поддерживаемые операторы
OPERATORS = {"NOT", "AND", "OR"}

# Приоритеты операторов
PRECEDENCE = {"NOT": 3, "AND": 2, "OR": 1}

# Ассоциативность операторов
ASSOC = {"NOT": "right", "AND": "left", "OR": "left"}


# Загрузка инвертированного индекса

def load_index(path: str) -> Dict[str, Set[str]]:
    """
    Загружает индекс из JSON файла.

    В JSON документы хранятся списками.
    Для работы с булевыми операциями преобразуем их в множества.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {term: set(docs) for term, docs in data.items()}


# Токенизация строки запроса

def tokenize_query(q: str) -> List[str]:
    """
    Разбивает строку запроса на токены.

    Операторы приводятся к верхнему регистру,
    термы — к нижнему.
    """
    raw = TOKEN_RE.findall(q)

    tokens = []
    for t in raw:
        up = t.upper()

        if up in OPERATORS or t in ("(", ")"):
            tokens.append(up if up in OPERATORS else t)
        else:
            tokens.append(t.lower())

    return tokens


# Добавление неявного оператора AND

def insert_implicit_and(tokens: List[str]) -> List[str]:
    """
    Добавляет оператор AND в случаях, когда он
    не указан явно.

    Примеры:
      "клеопатра цезарь" -> "клеопатра AND цезарь"
      "клеопатра (цезарь OR помпей)" -> "клеопатра AND (...)"
      ") клеопатра" -> ") AND клеопатра"
      "клеопатра NOT цезарь" -> "клеопатра AND NOT цезарь"
    """

    def is_term(x: str) -> bool:
        return x not in OPERATORS and x not in ("(", ")")

    out = []

    for t in tokens:
        if out:
            prev = out[-1]

            prev_is_term_or_rparen = (prev == ")") or is_term(prev)
            cur_is_term_or_lparen_or_not = (t == "(") or is_term(t) or (t == "NOT")

            if prev_is_term_or_rparen and cur_is_term_or_lparen_or_not:
                out.append("AND")

        out.append(t)

    return out


# Преобразование запроса в обратную польскую нотацию

def to_rpn(tokens: List[str]) -> List[str]:
    """
    Переводит инфиксное выражение в RPN
    (алгоритм shunting-yard).
    """
    output: List[str] = []
    stack: List[str] = []

    for t in tokens:

        if t == "(":
            stack.append(t)

        elif t == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())

            if not stack:
                raise ValueError("Лишняя закрывающая скобка")

            stack.pop()

        elif t in OPERATORS:

            while stack and stack[-1] in OPERATORS:
                top = stack[-1]

                if (ASSOC[t] == "left" and PRECEDENCE[t] <= PRECEDENCE[top]) or (
                    ASSOC[t] == "right" and PRECEDENCE[t] < PRECEDENCE[top]
                ):
                    output.append(stack.pop())
                else:
                    break

            stack.append(t)

        else:
            output.append(t)

    while stack:
        if stack[-1] in ("(", ")"):
            raise ValueError("Непарные скобки в запросе")

        output.append(stack.pop())

    return output


# Вычисление RPN выражения

def eval_rpn(rpn: List[str], index: Dict[str, Set[str]], universe: Set[str]) -> Set[str]:
    """
    Вычисляет результат булевого выражения
    над множествами документов.
    """
    stack: List[Set[str]] = []

    for t in rpn:

        if t not in OPERATORS:
            stack.append(index.get(t, set()))
            continue

        if t == "NOT":

            if not stack:
                raise ValueError("NOT без операнда")

            a = stack.pop()
            stack.append(universe - a)

        else:

            if len(stack) < 2:
                raise ValueError(f"{t} требует 2 операнда")

            b = stack.pop()
            a = stack.pop()

            if t == "AND":
                stack.append(a & b)

            elif t == "OR":
                stack.append(a | b)

    if len(stack) != 1:
        raise ValueError("Ошибка запроса")

    return stack[0]


# Выполнение поиска

def search(query: str, index: Dict[str, Set[str]]) -> List[str]:
    """
    Выполняет булев поиск по индексу.
    """

    universe = set()

    for docs in index.values():
        universe |= docs

    tokens = tokenize_query(query)
    tokens = insert_implicit_and(tokens)
    rpn = to_rpn(tokens)

    result = eval_rpn(rpn, index, universe)

    return sorted(result)


# Точка входа

def main():
    """
    CLI интерфейс для запуска поиска.
    """

    ap = argparse.ArgumentParser()

    ap.add_argument("--index", default="inverted_index.json", help="Путь к индексу")
    ap.add_argument("--query", "-q", required=True, help="Строка запроса")

    args = ap.parse_args()

    index = load_index(args.index)
    docs = search(args.query, index)

    print(f"Found: {len(docs)}")

    for d in docs:
        print(d)


if __name__ == "__main__":
    main()