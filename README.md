# my-test-project

A simple Flask API and greeting script.

## hello.py

A simple Python script that prompts the user for their name and prints a greeting.

```
python hello.py
```

## app.py

A Flask API with three endpoints for health checking and data storage.

### Setup

```
pip install flask
python app.py
```

The server runs on `http://localhost:5000` by default.

### Endpoints

#### GET /health

Returns the health status of the API.

```bash
curl http://localhost:5000/health
```

Response:
```json
{"status": "ok"}
```

---

#### POST /data

Stores a new entry. Requires a JSON body with `name` (non-empty string) and `value` fields.

```bash
curl -X POST http://localhost:5000/data \
  -H "Content-Type: application/json" \
  -d '{"name": "temperature", "value": 72.5}'
```

Response (201):
```json
{"message": "Data stored successfully", "data": {"name": "temperature", "value": 72.5}}
```

---

#### GET /data

Returns all stored entries and a count.

```bash
curl http://localhost:5000/data
```

Response:
```json
{"data": [{"name": "temperature", "value": 72.5}], "count": 1}
```
