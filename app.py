import sqlite3

from flask import Flask, g, request, jsonify

app = Flask(__name__)

DATABASE = "data.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute(
        "CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, value TEXT NOT NULL)"
    )
    db.commit()
    db.close()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/data", methods=["GET"])
def get_data():
    db = get_db()
    rows = db.execute("SELECT name, value FROM entries").fetchall()
    data = [{"name": row["name"], "value": row["value"]} for row in rows]
    return jsonify({"data": data, "count": len(data)})


@app.route("/data", methods=["POST"])
def store_data():
    body = request.get_json(silent=True)

    if body is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    name = body.get("name")
    value = body.get("value")

    if name is None or value is None:
        return jsonify({"error": "Both 'name' and 'value' fields are required"}), 400

    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "'name' must be a non-empty string"}), 400

    name = name.strip()
    db = get_db()
    db.execute("INSERT INTO entries (name, value) VALUES (?, ?)", (name, str(value)))
    db.commit()

    return jsonify({"message": "Data stored successfully", "data": {"name": name, "value": value}}), 201


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
