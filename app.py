from flask import Flask, request, render_template_string
from vector_search import vector_search


app = Flask(__name__)


HTML_PAGE = """
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Векторный поиск</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f7f7f7;
            color: #222;
        }

        h1 {
            margin-bottom: 20px;
        }

        form {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
        }

        input[type="text"] {
            flex: 1;
            padding: 12px;
            font-size: 16px;
        }

        button {
            padding: 12px 18px;
            font-size: 16px;
            cursor: pointer;
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .rank {
            font-weight: bold;
            color: #555;
        }

        .doc {
            font-size: 18px;
            margin: 6px 0;
        }

        .score {
            color: #006400;
        }

        .meta {
            color: #666;
            margin-bottom: 15px;
        }

        .empty {
            color: #a00;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Поисковая система (векторный поиск)</h1>

    <form method="get" action="/">
        <input
            type="text"
            name="q"
            placeholder="Введите запрос"
            value="{{ query }}"
            required
        >
        <button type="submit">Искать</button>
    </form>

    {% if searched %}
        <div class="meta">
            <div><strong>Запрос:</strong> {{ query }}</div>
            <div><strong>Найдено результатов:</strong> {{ results|length }}</div>
        </div>

        {% if results %}
            {% for doc, score in results %}
                <div class="card">
                    <div class="rank">Место: {{ loop.index }}</div>
                    <div class="doc">{{ doc }}</div>
                    <div class="score">Сходство: {{ "%.6f"|format(score) }}</div>
                </div>
            {% endfor %}
        {% else %}
            <div class="empty">По запросу ничего не найдено.</div>
        {% endif %}
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("q", "").strip()
    results = []
    searched = False
    error = None

    if query:
        searched = True
        try:
            results = vector_search(
                query=query,
                index_path="inverted_index.json",
                tfidf_dir="tfidf_lemmas",
                top_k=10,
            )
        except Exception as e:
            error = str(e)

    if error:
        return f"<h2>Ошибка</h2><pre>{error}</pre>", 500

    return render_template_string(
        HTML_PAGE,
        query=query,
        results=results,
        searched=searched,
    )


if __name__ == "__main__":
    app.run(debug=True)