from flask import Flask, request, jsonify

app = Flask(__name__)

data_store = []


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/data", methods=["GET"])
def get_data():
    return jsonify({"data": data_store, "count": len(data_store)})


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

    entry = {"name": name.strip(), "value": value}
    data_store.append(entry)

    return jsonify({"message": "Data stored successfully", "data": entry}), 201


if __name__ == "__main__":
    app.run(debug=True)
