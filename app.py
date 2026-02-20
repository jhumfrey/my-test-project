import os
import sqlite3

import anthropic
from flask import Flask, g, request, jsonify, render_template_string

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Data Entry</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; color: #1a1a1a; background: #f5f5f5; padding: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
    h2 { font-size: 1.1rem; margin: 2rem 0 0.75rem; }

    form { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem; max-width: 480px; display: grid; gap: 1rem; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; font-weight: 500; }
    input, select { padding: 0.5rem 0.75rem; border: 1px solid #ccc; border-radius: 5px; font-size: 1rem; background: #fff; }
    input:focus, select:focus { outline: none; border-color: #4f7dff; box-shadow: 0 0 0 3px rgba(79,125,255,.15); }
    button { padding: 0.6rem 1.25rem; background: #4f7dff; color: #fff; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer; justify-self: start; }
    button:hover { background: #3a6ae8; }

    #status { font-size: 0.875rem; min-height: 1.25rem; }
    #status.error { color: #c0392b; }
    #status.ok    { color: #27ae60; }

    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
    th, td { padding: 0.65rem 1rem; text-align: left; border-bottom: 1px solid #eee; font-size: 0.9rem; }
    th { background: #f0f0f0; font-weight: 600; white-space: nowrap; }
    tr:last-child td { border-bottom: none; }
    #empty-row td { color: #999; font-style: italic; }
  </style>
</head>
<body>
  <nav style="margin-bottom:1.5rem"><a href="/reports" style="color:#4f7dff;text-decoration:none;font-size:.9rem">Reports →</a></nav>
  <h1>Data Entry</h1>

  <form id="entry-form">
    <label>Full Name
      <input id="f-name" type="text" required placeholder="Jane Smith">
    </label>
    <label>Date of Birth
      <input id="f-dob" type="date">
    </label>
    <label>Zip Code
      <input id="f-zip" type="text" pattern="[0-9]{5}" maxlength="5" placeholder="10001">
    </label>
    <label>Race
      <select id="f-race">
        <option value="">— Select —</option>
        <option>American Indian or Alaska Native</option>
        <option>Asian</option>
        <option>Black or African American</option>
        <option>Native Hawaiian or Other Pacific Islander</option>
        <option>White</option>
        <option>Two or more races</option>
        <option>Prefer not to say</option>
      </select>
    </label>
    <label>Ethnicity
      <select id="f-ethnicity">
        <option value="">— Select —</option>
        <option>Hispanic or Latino</option>
        <option>Not Hispanic or Latino</option>
        <option>Prefer not to say</option>
      </select>
    </label>
    <div id="status"></div>
    <button type="submit">Submit</button>
  </form>

  <h2>All Entries</h2>
  <table>
    <thead>
      <tr>
        <th>Full Name</th>
        <th>Date of Birth</th>
        <th>Zip Code</th>
        <th>Race</th>
        <th>Ethnicity</th>
      </tr>
    </thead>
    <tbody id="entries-body"></tbody>
  </table>

  <script>
    function cell(text) {
      const td = document.createElement('td');
      td.textContent = text || '—';
      return td;
    }

    async function loadEntries() {
      const res = await fetch('/data');
      const body = await res.json();
      const tbody = document.getElementById('entries-body');
      tbody.innerHTML = '';
      if (body.data.length === 0) {
        tbody.innerHTML = '<tr id="empty-row"><td colspan="5">No entries yet.</td></tr>';
        return;
      }
      for (const entry of body.data) {
        let demo = {};
        try { demo = JSON.parse(entry.value); } catch {}
        const tr = document.createElement('tr');
        tr.appendChild(cell(entry.name));
        tr.appendChild(cell(demo.dob));
        tr.appendChild(cell(demo.zip));
        tr.appendChild(cell(demo.race));
        tr.appendChild(cell(demo.ethnicity));
        tbody.appendChild(tr);
      }
    }

    document.getElementById('entry-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const status = document.getElementById('status');
      status.className = '';
      status.textContent = '';

      const name  = document.getElementById('f-name').value.trim();
      const value = JSON.stringify({
        dob:       document.getElementById('f-dob').value,
        zip:       document.getElementById('f-zip').value.trim(),
        race:      document.getElementById('f-race').value,
        ethnicity: document.getElementById('f-ethnicity').value,
      });

      const res = await fetch('/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, value }),
      });

      if (res.ok) {
        e.target.reset();
        status.className = 'ok';
        status.textContent = 'Entry saved.';
        await loadEntries();
      } else {
        const err = await res.json();
        status.className = 'error';
        status.textContent = err.error || 'Something went wrong.';
      }
    });

    loadEntries();
  </script>
</body>
</html>"""

REPORTS_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reports</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; color: #1a1a1a; background: #f5f5f5; padding: 2rem; }
    h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
    h2 { font-size: 1.1rem; margin: 2rem 0 0.75rem; }
    nav { margin-bottom: 1.5rem; }
    nav a { color: #4f7dff; text-decoration: none; font-size: 0.9rem; }
    nav a:hover { text-decoration: underline; }

    .query-box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem; max-width: 640px; display: grid; gap: 1rem; }
    .examples { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .chip { padding: 0.3rem 0.75rem; background: #eef2ff; border: 1px solid #c7d4ff; border-radius: 999px; font-size: 0.8rem; color: #3a5fd9; cursor: pointer; white-space: nowrap; }
    .chip:hover { background: #dce6ff; }
    .input-row { display: flex; gap: 0.5rem; }
    input[type=text] { flex: 1; padding: 0.5rem 0.75rem; border: 1px solid #ccc; border-radius: 5px; font-size: 1rem; }
    input[type=text]:focus { outline: none; border-color: #4f7dff; box-shadow: 0 0 0 3px rgba(79,125,255,.15); }
    button { padding: 0.6rem 1.25rem; background: #4f7dff; color: #fff; border: none; border-radius: 5px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #3a6ae8; }
    button:disabled { background: #a0b4f0; cursor: not-allowed; }

    #status { font-size: 0.875rem; min-height: 1.25rem; color: #c0392b; }

    .chart-tabs { display: flex; gap: 0.25rem; margin-bottom: 1rem; }
    .tab-btn { padding: 0.35rem 1rem; border: 1px solid #ccc; border-radius: 5px; background: #f5f5f5; font-size: 0.875rem; cursor: pointer; color: #444; }
    .tab-btn.active { background: #4f7dff; color: #fff; border-color: #4f7dff; }
    .tab-btn:hover:not(.active) { background: #e8e8e8; }
    .sql-block { max-width: 640px; margin-top: 1.5rem; }
    .sql-block h2 { margin-bottom: 0.5rem; }
    pre { background: #1e1e1e; color: #d4d4d4; border-radius: 6px; padding: 1rem 1.25rem; font-size: 0.8rem; white-space: pre-wrap; word-break: break-all; overflow-x: auto; }

    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
    th, td { padding: 0.65rem 1rem; text-align: left; border-bottom: 1px solid #eee; font-size: 0.9rem; }
    th { background: #f0f0f0; font-weight: 600; white-space: nowrap; }
    tr:last-child td { border-bottom: none; }
    .no-results td { color: #999; font-style: italic; }

    .spinner { display: inline-block; width: 0.9rem; height: 0.9rem; border: 2px solid #ccc; border-top-color: #4f7dff; border-radius: 50%; animation: spin 0.6s linear infinite; vertical-align: middle; margin-right: 0.4rem; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <nav><a href="/">← Data Entry</a></nav>
  <h1>Reports</h1>

  <div class="query-box">
    <div class="examples">
      <span class="chip">How many people by race?</span>
      <span class="chip">Average age by ethnicity</span>
      <span class="chip">Top 10 most common zip codes</span>
      <span class="chip">Count by race and ethnicity</span>
      <span class="chip">How many people born each year?</span>
      <span class="chip">Youngest and oldest person</span>
    </div>
    <div class="input-row">
      <input id="q-input" type="text" placeholder="Ask a question about the data…">
      <button id="q-btn">Ask</button>
    </div>
    <div id="status"></div>
  </div>

  <div id="results-section" style="display:none">
    <h2>Results</h2>
    <div id="chart-section" style="max-width:640px; background:#fff; border:1px solid #ddd; border-radius:8px; padding:1.25rem; margin-bottom:1.5rem; display:none">
      <div class="chart-tabs">
        <button class="tab-btn active" data-tab="bar">Bar</button>
        <button class="tab-btn" data-tab="pie">Pie</button>
        <button class="tab-btn" data-tab="line">Line</button>
      </div>
      <div class="tab-panel" id="panel-bar"><canvas id="chart-bar"></canvas></div>
      <div class="tab-panel" id="panel-pie" style="display:none"><canvas id="chart-pie"></canvas></div>
      <div class="tab-panel" id="panel-line" style="display:none"><canvas id="chart-line"></canvas></div>
    </div>
    <table>
      <thead id="results-head"></thead>
      <tbody id="results-body"></tbody>
    </table>
    <div class="sql-block">
      <h2>Generated SQL</h2>
      <pre id="sql-display"></pre>
    </div>
  </div>

  <script>
    const input   = document.getElementById('q-input');
    const btn     = document.getElementById('q-btn');
    const status  = document.getElementById('status');
    const section = document.getElementById('results-section');
    const chartInstances = { bar: null, pie: null, line: null };

    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => { p.style.display = 'none'; });
        btn.classList.add('active');
        document.getElementById('panel-' + btn.dataset.tab).style.display = '';
      });
    });

    document.querySelectorAll('.chip').forEach(chip => {
      chip.addEventListener('click', () => { input.value = chip.textContent; runQuery(); });
    });
    btn.addEventListener('click', runQuery);
    input.addEventListener('keydown', e => { if (e.key === 'Enter') runQuery(); });

    async function runQuery() {
      const question = input.value.trim();
      if (!question) return;

      status.innerHTML = '<span class="spinner"></span>Generating query\u2026';
      btn.disabled = true;
      section.style.display = 'none';

      try {
        const res  = await fetch('/reports/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question }),
        });
        const body = await res.json();

        if (!res.ok) {
          status.textContent = body.error || 'Something went wrong.';
          if (body.sql) showSql(body.sql);
          return;
        }

        status.textContent = '';
        showSql(body.sql);
        showCharts(body.columns, body.rows);
        showTable(body.columns, body.rows);
        section.style.display = '';
      } catch (err) {
        status.textContent = 'Request failed: ' + err.message;
      } finally {
        btn.disabled = false;
      }
    }

    function showSql(sql) {
      document.getElementById('sql-display').textContent = sql;
      section.style.display = '';
    }

    const PALETTE = [
      'rgba(79,125,255,0.8)',  'rgba(255,99,132,0.8)',  'rgba(54,162,235,0.8)',
      'rgba(255,206,86,0.8)',  'rgba(75,192,192,0.8)',  'rgba(153,102,255,0.8)',
      'rgba(255,159,64,0.8)',  'rgba(199,199,199,0.8)', 'rgba(83,102,255,0.8)',
      'rgba(255,99,255,0.8)',
    ];
    const PALETTE_BORDER = PALETTE.map(c => c.replace('0.8', '1'));

    function isNumericCol(rows, ci) {
      return rows.length > 0 && rows.every(r => r[ci] === null || r[ci] === '' || !isNaN(parseFloat(r[ci])));
    }

    function showCharts(columns, rows) {
      const chartSection = document.getElementById('chart-section');
      for (const key of Object.keys(chartInstances)) {
        if (chartInstances[key]) { chartInstances[key].destroy(); chartInstances[key] = null; }
      }

      if (!rows.length) { chartSection.style.display = 'none'; return; }

      const numericCols = [];
      for (let i = 1; i < columns.length; i++) {
        if (isNumericCol(rows, i)) numericCols.push(i);
      }
      if (!numericCols.length) { chartSection.style.display = 'none'; return; }

      chartSection.style.display = '';
      const labels = rows.map(r => r[0] !== null ? String(r[0]) : '\u2014');

      // Rebuild canvases to avoid Chart.js reuse issues
      for (const t of ['bar', 'pie', 'line']) {
        document.getElementById('panel-' + t).innerHTML = `<canvas id="chart-${t}"></canvas>`;
      }

      // Bar chart
      chartInstances.bar = new Chart(document.getElementById('chart-bar'), {
        type: 'bar',
        data: {
          labels,
          datasets: numericCols.map((ci, idx) => ({
            label: columns[ci],
            data: rows.map(r => parseFloat(r[ci]) ?? null),
            backgroundColor: PALETTE[idx % PALETTE.length],
            borderColor: PALETTE_BORDER[idx % PALETTE_BORDER.length],
            borderWidth: 1,
          })),
        },
        options: {
          responsive: true,
          plugins: { legend: { display: numericCols.length > 1 } },
          scales: {
            x: { grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
          },
        },
      });

      // Pie chart (first numeric column only)
      const pieData = rows.map(r => parseFloat(r[numericCols[0]]) || 0);
      chartInstances.pie = new Chart(document.getElementById('chart-pie'), {
        type: 'pie',
        data: {
          labels,
          datasets: [{
            data: pieData,
            backgroundColor: PALETTE.slice(0, pieData.length),
            borderColor: PALETTE_BORDER.slice(0, pieData.length),
            borderWidth: 1,
          }],
        },
        options: { responsive: true, plugins: { legend: { position: 'right' } } },
      });

      // Line chart
      chartInstances.line = new Chart(document.getElementById('chart-line'), {
        type: 'line',
        data: {
          labels,
          datasets: numericCols.map((ci, idx) => ({
            label: columns[ci],
            data: rows.map(r => parseFloat(r[ci]) ?? null),
            backgroundColor: PALETTE[idx % PALETTE.length],
            borderColor: PALETTE_BORDER[idx % PALETTE_BORDER.length],
            borderWidth: 2,
            fill: false,
            tension: 0.3,
            pointRadius: 4,
          })),
        },
        options: {
          responsive: true,
          plugins: { legend: { display: numericCols.length > 1 } },
          scales: {
            x: { grid: { color: 'rgba(0,0,0,0.05)' } },
            y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
          },
        },
      });

      // Reset to bar tab
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => { p.style.display = 'none'; });
      document.querySelector('.tab-btn[data-tab="bar"]').classList.add('active');
      document.getElementById('panel-bar').style.display = '';
    }

    function showTable(columns, rows) {
      const head = document.getElementById('results-head');
      const body = document.getElementById('results-body');
      head.innerHTML = '';
      body.innerHTML = '';

      const hr = document.createElement('tr');
      columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        hr.appendChild(th);
      });
      head.appendChild(hr);

      if (rows.length === 0) {
        body.innerHTML = `<tr class="no-results"><td colspan="${columns.length}">No results.</td></tr>`;
        return;
      }
      rows.forEach(row => {
        const tr = document.createElement('tr');
        row.forEach(val => {
          const td = document.createElement('td');
          td.textContent = (val !== null && val !== undefined) ? val : '\u2014';
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }
  </script>
</body>
</html>"""

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


SCHEMA_PROMPT = """You are a SQLite expert. Given a natural language question, return a single valid SQLite SELECT query — nothing else. No explanation, no markdown, no code fences.

Schema:
  Table: entries
  Columns:
    id      INTEGER  primary key
    name    TEXT     person's full name (e.g. "Jane Smith")
    value   TEXT     JSON string — access fields with json_extract():
      json_extract(value, '$.dob')       → date of birth, YYYY-MM-DD string
      json_extract(value, '$.zip')       → 5-digit zip code string
      json_extract(value, '$.race')      → race category string
      json_extract(value, '$.ethnicity') → ethnicity category string

  Race values: "White", "Black or African American", "Asian",
               "American Indian or Alaska Native",
               "Native Hawaiian or Other Pacific Islander",
               "Two or more races", "Prefer not to say"

  Ethnicity values: "Hispanic or Latino", "Not Hispanic or Latino", "Prefer not to say"

  Age in years:
    (strftime('%Y','now') - strftime('%Y', json_extract(value,'$.dob')))
    - (strftime('%m-%d','now') < strftime('%m-%d', json_extract(value,'$.dob')))

Rules:
  - SELECT only. No INSERT, UPDATE, DELETE, DROP, or any other statement type.
  - Use descriptive column aliases (e.g. AS "Count", AS "Race", AS "Avg Age").
  - LIMIT 100 unless the question implies a different limit.
  - If the question mentions charts, graphs, or visualizations, generate the SQL anyway — the application handles all rendering independently."""


def generate_sql(question):
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SCHEMA_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    sql = msg.content[0].text.strip()
    # Strip markdown fences if the model included them despite instructions
    if sql.startswith("```"):
        sql = "\n".join(l for l in sql.splitlines() if not l.startswith("```")).strip()
    return sql


@app.route("/", methods=["GET"])
def index():
    return render_template_string(PAGE)


@app.route("/reports", methods=["GET"])
def reports():
    return render_template_string(REPORTS_PAGE)


@app.route("/reports/query", methods=["POST"])
def reports_query():
    body = request.get_json(silent=True)
    if not body or not body.get("question", "").strip():
        return jsonify({"error": "A non-empty 'question' field is required"}), 400

    question = body["question"].strip()

    try:
        sql = generate_sql(question)
    except anthropic.AuthenticationError:
        return jsonify({"error": "Anthropic API key is missing or invalid. Set the ANTHROPIC_API_KEY environment variable."}), 502
    except Exception as e:
        return jsonify({"error": f"Failed to generate SQL: {e}"}), 502

    if not sql.upper().lstrip().startswith("SELECT"):
        return jsonify({"error": "Only SELECT queries are permitted.", "sql": sql}), 400

    try:
        cursor = get_db().execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
    except Exception as e:
        return jsonify({"error": f"Query failed: {e}", "sql": sql}), 400

    return jsonify({"columns": columns, "rows": rows, "sql": sql})


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
