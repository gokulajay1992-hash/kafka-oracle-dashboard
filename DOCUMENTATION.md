# Kafka → Oracle Pipeline Dashboard — Full Code Documentation

> Written for someone with **no Python background**.
> Every line is explained in plain English.

---

## How the app works — Big Picture

```
Kafka Topic  →  pipeline.py reads messages
                    ↓
              xml_converter.py converts XML to JSON
                    ↓
              db_handler.py saves JSON to Oracle DB
                    ↓
              app.py shows everything on the dashboard
```

The app has **5 source files** and **1 config file**.
You only need to edit `config.py`. The rest runs automatically.

---

## File 1 — `config.py`  (Your settings file)

This file holds all the connection details. Think of it like a settings panel.
**You must fill this in before running the app.**

```python
KAFKA_CONFIG = {
```
- `KAFKA_CONFIG` is a **dictionary** (like a labeled box with compartments).
- A dictionary stores pairs of `"key": value`.

```python
    "bootstrap_servers": "localhost:9092",
```
- The address of your Kafka server.
- `localhost` means "same machine". Replace with your server's IP/hostname.
- `9092` is the default Kafka port number.

```python
    "topic": "your-topic-name",
```
- The name of the Kafka topic (like a queue/channel) to read messages from.

```python
    "group_id": "kafka-oracle-dashboard-group",
```
- A name for this consumer. Kafka uses this to remember which messages have been read.
- Multiple apps can read the same topic under different group IDs independently.

```python
    "auto_offset_reset": "latest",
```
- Tells Kafka where to start reading when the consumer connects for the first time.
- `"latest"` = only read new messages from now onward.
- `"earliest"` = read all messages from the very beginning.

```python
    "security_protocol": "PLAINTEXT",
```
- How the connection to Kafka is secured.
- `PLAINTEXT` = no encryption (for internal/dev environments).
- Other options: `SSL`, `SASL_SSL` (for production with authentication).

---

```python
ORACLE_CONFIG = {
    "host": "localhost",
```
- The server address where your Oracle database is running.

```python
    "port": 1521,
```
- The port Oracle listens on. 1521 is Oracle's default.

```python
    "service_name": "ORCL",
```
- The name of the Oracle database service/instance.

```python
    "username": "your_db_user",
    "password": "your_db_password",
```
- Your Oracle login credentials.

```python
    "table_name": "your_table_name",
```
- The exact name of the table where records already exist.

```python
    "reference_id_column": "reference_id",
```
- The column in your table that contains the reference ID (used to find the row).

```python
    "json_data_column": "json_data",
```
- The empty column in your table where the converted JSON will be saved.

---

```python
REFERENCE_ID_PATH = "root.header.referenceId"
```
- Tells the app where to find the reference ID inside your XML message.
- Uses dot notation to navigate nested XML tags.
- Example: if your XML is `<root><header><referenceId>ABC123</referenceId></header></root>`,
  the path is `root.header.referenceId`.

```python
REFRESH_INTERVAL_SECONDS = 3
```
- How often (in seconds) the dashboard automatically refreshes when auto-refresh is on.

```python
MAX_LOG_ENTRIES = 500
```
- Maximum number of log lines kept in memory. Older logs are dropped when this limit is hit.

---

## File 2 — `xml_converter.py`  (Converts XML to JSON)

This file has two jobs:
1. Convert an XML string into JSON format.
2. Extract the reference ID value from the converted data.

---

```python
import json
import xmltodict
```
- `import` means "load this external tool/library so we can use it."
- `json` — Python's built-in tool for reading and writing JSON.
- `xmltodict` — an installed library that reads XML and turns it into a Python dictionary.

---

```python
def xml_to_json(xml_string: str) -> tuple[str | None, str | None]:
```
- `def` means "define a function" — a reusable block of code with a name.
- Function name: `xml_to_json`
- `xml_string: str` — expects one input: a text string containing XML.
- `-> tuple[str | None, str | None]` — this function always returns TWO values:
  - First value: the JSON string (or `None` if something went wrong)
  - Second value: an error message (or `None` if everything was fine)

```python
    try:
```
- `try` means "attempt the following code, and if anything breaks, go to `except`."

```python
        parsed = xmltodict.parse(xml_string, force_list=False)
```
- Calls `xmltodict.parse()` to convert the XML text into a Python dictionary.
- `force_list=False` means: don't force single items into a list unnecessarily.
- The result is stored in `parsed`.

```python
        return json.dumps(parsed, ensure_ascii=False), None
```
- `json.dumps()` converts the Python dictionary into a JSON-formatted text string.
- `ensure_ascii=False` allows non-English characters (accents, etc.) to pass through as-is.
- Returns the JSON string AND `None` (no error).

```python
    except Exception as exc:
        return None, str(exc)
```
- If anything in the `try` block fails, Python jumps here.
- `Exception` catches any type of error.
- `exc` holds the error details.
- Returns `None` (no JSON) AND the error message as text.

---

```python
def extract_by_path(data: dict, dotted_path: str):
```
- Function name: `extract_by_path`
- Takes a dictionary (`data`) and a dotted path string like `"root.header.referenceId"`.
- Walks into the nested dictionary step by step to find the value.

```python
    keys = dotted_path.split(".")
```
- `.split(".")` breaks the string `"root.header.referenceId"` into a list: `["root", "header", "referenceId"]`.

```python
    current = data
```
- Start at the top of the dictionary.

```python
    for key in keys:
```
- Loop through each key in the list one by one (`root`, then `header`, then `referenceId`).

```python
        if isinstance(current, dict):
```
- Check if the current position in the data is still a dictionary (nested object).

```python
            if key not in current:
                raise KeyError(...)
```
- If the key doesn't exist at this level, raise an error with a helpful message.

```python
            current = current[key]
```
- Move one level deeper into the dictionary using this key.

```python
        else:
            raise TypeError(...)
```
- If we expected a dictionary but got something else (like a plain text value), raise an error.

```python
    return current
```
- After all keys have been traversed, return the final value (the reference ID).

---

## File 3 — `db_handler.py`  (Talks to Oracle database)

This file handles all communication with Oracle. It has three functions.

---

```python
import oracledb
from config import ORACLE_CONFIG
```
- `oracledb` — the library that connects Python to Oracle Database.
- `from config import ORACLE_CONFIG` — pulls the Oracle settings dictionary from `config.py`.

---

```python
def _get_dsn() -> str:
    cfg = ORACLE_CONFIG
    return f"{cfg['host']}:{cfg['port']}/{cfg['service_name']}"
```
- Builds the Oracle connection string (called DSN = Data Source Name).
- Example result: `"localhost:1521/ORCL"`
- The `f"..."` is an f-string — it embeds variable values directly into the text.
- Functions starting with `_` (underscore) are internal helpers, not meant to be called from outside.

---

```python
def get_connection():
```
- Opens and returns a live connection to the Oracle database.

```python
    return oracledb.connect(
        user=ORACLE_CONFIG["username"],
        password=ORACLE_CONFIG["password"],
        dsn=_get_dsn(),
    )
```
- `oracledb.connect()` — creates the database connection using the credentials and DSN.
- This uses "thin mode" — meaning it does NOT require Oracle Client software installed on the PC.

---

```python
def test_connection() -> tuple[bool, str]:
```
- A quick test to check if Oracle is reachable.
- Returns two values: `True/False` (success or failure) and a message string.

```python
    try:
        conn = get_connection()
        conn.close()
        return True, "Oracle connection successful."
    except Exception as exc:
        return False, str(exc)
```
- Try to open a connection, then immediately close it (just checking if it works).
- If it works: return `True` with a success message.
- If it fails: return `False` with the error message.

---

```python
def update_first_record(reference_id: str, json_data: str) -> tuple[bool, str]:
```
- The main function — finds a row in the DB by reference_id and updates it with JSON.
- Returns `True/False` and a status message.

```python
    table = ORACLE_CONFIG["table_name"]
    ref_col = ORACLE_CONFIG["reference_id_column"]
    json_col = ORACLE_CONFIG["json_data_column"]
```
- Read the table and column names from config into short variable names for convenience.

```python
    select_sql = (
        f"SELECT ROWID FROM {table} "
        f"WHERE {ref_col} = :ref_id "
        f"AND ROWNUM = 1 "
        f"ORDER BY ROWID"
    )
```
- Builds a SQL SELECT query as a text string.
- `ROWID` — Oracle's internal unique row identifier (like a row's physical address in storage).
- `WHERE {ref_col} = :ref_id` — find rows where the reference_id column equals our value. `:ref_id` is a placeholder filled in safely later (prevents SQL injection).
- `ROWNUM = 1` — only return the first match.
- `ORDER BY ROWID` — among duplicates, take the one inserted earliest.

```python
    update_sql = (
        f"UPDATE {table} SET {json_col} = :json_data "
        f"WHERE ROWID = :row_id"
    )
```
- Builds the SQL UPDATE query.
- Updates only the exact row found above (using its ROWID).
- `:json_data` and `:row_id` are placeholders filled in safely at runtime.

```python
    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
```
- Open a database connection.
- Create a `cursor` — think of it as a "pen" used to write/read SQL against the database.

```python
            cur.execute(select_sql, ref_id=reference_id)
```
- Run the SELECT query. The `:ref_id` placeholder gets filled with the actual `reference_id` value.

```python
            row = cur.fetchone()
```
- `fetchone()` retrieves the first (and only, due to ROWNUM=1) result row.

```python
            if not row:
                return False, f"No record found for reference_id '{reference_id}'"
```
- If no row was returned, report failure — the reference_id doesn't exist in the table.

```python
            row_id = row[0]
```
- `row` is a tuple (like a single-item list). `row[0]` gets the first (and only) value: the ROWID.

```python
            cur.execute(update_sql, json_data=json_data, row_id=row_id)
            conn.commit()
            return True, f"Updated row for reference_id '{reference_id}'"
```
- Run the UPDATE query using the ROWID we found.
- `conn.commit()` — save the change permanently to the database. Without commit, the change is temporary.
- Return success.

```python
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
```
- If any DB operation fails: `rollback()` cancels any partial changes (keeps the DB clean).
- Return the error message.

```python
        finally:
            conn.close()
```
- `finally` always runs — whether success or failure — to close the database connection and free resources.

---

## File 4 — `pipeline.py`  (The engine — reads Kafka, processes messages)

This is the most complex file. It runs a **background thread** (a separate task running in parallel)
that continuously reads from Kafka and processes each message.

---

```python
import json
import threading
import time
from datetime import datetime
```
- `json` — to parse/create JSON.
- `threading` — allows running code in the background while the dashboard stays responsive.
- `time` — for time-related operations.
- `datetime` — to get the current date and time for log timestamps.

```python
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
```
- `KafkaConsumer` — the class (blueprint) used to connect to and read from Kafka.
- `NoBrokersAvailable` — a specific error that occurs when Kafka can't be reached.

```python
from config import KAFKA_CONFIG, MAX_LOG_ENTRIES, REFERENCE_ID_PATH
from db_handler import update_first_record
from xml_converter import extract_by_path, xml_to_json
```
- Import settings and functions from our other files.

---

### The `ConsumerState` class

```python
class ConsumerState:
```
- A `class` is a blueprint for creating an object that holds both **data** and **actions** together.
- `ConsumerState` tracks everything about the running consumer: counters, logs, status.

```python
    def __init__(self):
```
- `__init__` is the constructor — it runs automatically when you create a `ConsumerState` object.
- Think of it as "set up the initial state when born."

```python
        self._lock = threading.Lock()
```
- A **lock** is like a mutex/semaphore. It prevents two threads from modifying the same data at the same time (avoids data corruption).
- `self._lock` means "this object's lock" — `self` always refers to the current object instance.

```python
        self.running: bool = False
```
- A flag (True/False) tracking whether the consumer is currently active.

```python
        self.processed: int = 0
        self.failed: int = 0
```
- Counters for successful and failed messages. Start at zero.

```python
        self._logs: list[dict] = []
```
- A list of log entries. Each entry is a dictionary with timestamp, level, reference_id, message.

```python
        self._timeline: list[dict] = []
```
- Stores snapshots of processed/failed counts over time — used to draw the line chart.

---

```python
    def log(self, level: str, message: str, reference_id: str = "-"):
```
- Adds a new log entry.
- `level` = "SUCCESS", "INFO", "ERROR", or "WARNING"
- `reference_id = "-"` means if no reference_id is provided, it defaults to `"-"`.

```python
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ...
        }
```
- `datetime.now()` gets the current date and time.
- `.strftime(...)` formats it as a readable string like `"2026-04-08 14:30:22"`.

```python
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > MAX_LOG_ENTRIES:
                self._logs = self._logs[-MAX_LOG_ENTRIES:]
```
- `with self._lock:` — acquire the lock before modifying the list, release it after. This is thread-safe.
- `.append(entry)` — add the new log entry to the end of the list.
- If the list exceeds 500 entries, keep only the last 500 (`[-500:]` means "last 500 items").

---

```python
    def inc_processed(self):
        with self._lock:
            self.processed += 1
            self._push_timeline()
```
- Increment the processed counter by 1 (thread-safely) and record a timeline snapshot.

```python
    def _push_timeline(self):
        self._timeline.append({
            "ts": datetime.now().strftime("%H:%M:%S"),
            "processed": self.processed,
            "failed": self.failed,
        })
        if len(self._timeline) > 300:
            self._timeline = self._timeline[-300:]
```
- Save a snapshot of current counts with a timestamp for the chart.
- Keep only the last 300 snapshots.

---

```python
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running": self.running,
                "processed": self.processed,
                "failed": self.failed,
                "logs": list(reversed(self._logs)),
                "timeline": list(self._timeline),
            }
```
- Returns a copy of all current state for the dashboard to display.
- `list(reversed(...))` — reverses the log list so newest entries appear first in the table.
- Making copies (`list(...)`) prevents the dashboard from accidentally modifying the live data.

---

```python
    def start(self):
        with self._lock:
            if self.running:
                return
            self.running = True

        self._thread = threading.Thread(
            target=_run_consumer,
            args=(self,),
            daemon=True,
            name="kafka-consumer",
        )
        self._thread.start()
```
- If already running, do nothing and return.
- Otherwise, set `running = True` and create a new **thread**.
- `threading.Thread(target=_run_consumer, ...)` — creates a background task that will run `_run_consumer`.
- `daemon=True` — the thread automatically stops when the main app exits (no zombie processes).
- `.start()` — launches the thread.

```python
    def stop(self):
        with self._lock:
            self.running = False
```
- Sets `running = False`. The consumer loop checks this flag and stops itself gracefully.

---

```python
state = ConsumerState()
```
- Create **one single instance** of ConsumerState at module level.
- This object lives as long as the app is running — it survives each dashboard refresh.

---

```python
def _build_kafka_consumer() -> KafkaConsumer:
    kwargs = {
        "bootstrap_servers": ...,
        "value_deserializer": lambda m: m.decode("utf-8", errors="replace"),
        "consumer_timeout_ms": 1000,
        ...
    }
```
- `kwargs` (keyword arguments) — a dictionary of settings passed to KafkaConsumer.
- `lambda m: m.decode("utf-8", errors="replace")` — a tiny inline function:
  - Kafka delivers messages as raw bytes. This decodes them to a Python text string.
  - `errors="replace"` — if a byte can't be decoded, replace it with `?` instead of crashing.
- `consumer_timeout_ms=1000` — if no messages arrive for 1 second, raise `StopIteration` (used to check if we should stop).

```python
    return KafkaConsumer(KAFKA_CONFIG["topic"], **kwargs)
```
- Create and return the Kafka consumer. `**kwargs` unpacks the dictionary as named arguments.

---

```python
def _run_consumer(s: ConsumerState):
    try:
        consumer = _build_kafka_consumer()
    except NoBrokersAvailable as exc:
        s.log("ERROR", f"Cannot reach Kafka brokers: {exc}")
        s.running = False
        return
```
- Try to connect to Kafka. If brokers can't be found, log the error, mark as stopped, and exit.

```python
    try:
        while s.running:
            try:
                for msg in consumer:
                    if not s.running:
                        break
                    _process_message(msg.value, s)
            except StopIteration:
                pass
```
- `while s.running:` — keep looping as long as the consumer should run.
- `for msg in consumer:` — iterate over incoming Kafka messages.
- `msg.value` — the decoded text content of the message.
- If no messages arrive for 1 second (`consumer_timeout_ms`), `StopIteration` is raised — we catch it with `pass` (ignore it) and loop again.

```python
    finally:
        consumer.close()
        s.running = False
        s.log("INFO", "Kafka consumer closed.")
```
- Always close the Kafka connection cleanly when the loop ends (whether stopped or crashed).

---

```python
def _process_message(raw: str, s: ConsumerState):
    # Step 1: XML → JSON
    json_str, err = xml_to_json(raw)
    if err:
        s.inc_failed()
        s.log("ERROR", f"XML parse failed: {err}")
        return
```
- Call `xml_to_json` with the raw XML text.
- If it returns an error, count it as failed, log the error, and `return` (stop processing this message).

```python
    # Step 2: Extract reference_id
    try:
        parsed = json.loads(json_str)
        reference_id = str(extract_by_path(parsed, REFERENCE_ID_PATH))
    except (KeyError, TypeError, ValueError) as exc:
        s.inc_failed()
        s.log("ERROR", ...)
        return
```
- `json.loads()` converts the JSON text string back into a Python dictionary.
- `extract_by_path()` navigates the dictionary to find the reference_id value.
- `str(...)` converts the value to text (in case it's a number).
- If anything fails, count as failed and stop.

```python
    # Step 3: Save to Oracle
    ok, msg = update_first_record(reference_id, json_str)
    if ok:
        s.inc_processed()
        s.log("SUCCESS", msg, reference_id)
    else:
        s.inc_failed()
        s.log("ERROR", f"DB update failed: {msg}", reference_id)
```
- Call `update_first_record()` to save the JSON to Oracle.
- If successful: increment processed counter and log SUCCESS.
- If failed: increment failed counter and log the error.

---

## File 5 — `app.py`  (The visual dashboard)

This is the Streamlit web application. Streamlit runs this file top-to-bottom every time
the page refreshes (which happens automatically every 3 seconds, or when you click a button).

---

```python
import time
import pandas as pd
import streamlit as st
```
- `time` — for the sleep/pause used in auto-refresh.
- `pandas` (alias `pd`) — a powerful data table library. Used to display the log table.
- `streamlit` (alias `st`) — the web dashboard framework. `st.something()` draws UI elements.

```python
from config import KAFKA_CONFIG, ORACLE_CONFIG, REFRESH_INTERVAL_SECONDS
from db_handler import test_connection
from pipeline import state as consumer_state
```
- Import settings, the DB connection tester, and the running consumer state object.

---

```python
st.set_page_config(
    page_title="Kafka → Oracle Pipeline",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
```
- Must be the **first** Streamlit call. Sets the browser tab title, icon, and layout.
- `layout="wide"` — use the full browser width instead of a narrow centered column.

---

```python
st.markdown("""<style> ... </style>""", unsafe_allow_html=True)
```
- Injects custom CSS styling into the page.
- Defines colored badge styles for SUCCESS (green), INFO (blue), ERROR (red), WARNING (yellow).
- `unsafe_allow_html=True` — allows HTML/CSS to be rendered (disabled by default for security).

---

```python
with st.sidebar:
```
- Everything indented inside this block appears in the left sidebar panel.

```python
    with st.expander("Kafka", expanded=True):
        st.code(...)
```
- `st.expander` creates a collapsible section.
- `st.code(...)` displays text in a monospace code block — used to show current config values.

```python
    if st.button("🔌 Test Oracle Connection", use_container_width=True):
        ok, msg = test_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)
```
- `st.button(...)` draws a clickable button.
- When clicked, Streamlit reruns the script and this `if` block executes.
- `st.success(...)` shows a green banner. `st.error(...)` shows a red banner.

```python
    col_start, col_stop = st.columns(2)
```
- `st.columns(2)` splits the sidebar into 2 equal columns side by side.
- Returns two column objects assigned to `col_start` and `col_stop`.

```python
    with col_start:
        if st.button("▶ Start", ...):
            if not consumer_state.running:
                consumer_state.start()
            else:
                st.toast("Consumer is already running.", icon="ℹ️")
```
- Draw the Start button in the left column.
- If clicked and not already running: start the consumer.
- `st.toast(...)` shows a temporary popup notification.

```python
    auto_refresh = st.toggle(f"Auto-refresh ({REFRESH_INTERVAL_SECONDS}s)", ...)
    st.session_state["auto_refresh"] = auto_refresh
```
- `st.toggle(...)` draws an on/off switch.
- `st.session_state` is a dictionary that persists values between reruns (like browser memory).

---

```python
snap = consumer_state.snapshot()
```
- Get a frozen copy of all current state (counters, logs, timeline) from the running pipeline.

```python
if snap["running"]:
    st.success("🟢  Consumer is running...")
else:
    st.warning("🔴  Consumer is stopped...")
```
- Show a green or red status banner depending on whether the consumer is active.

---

```python
total = snap["processed"] + snap["failed"]
success_rate = (snap["processed"] / total * 100) if total > 0 else 0.0
```
- Calculate total messages and success rate percentage.
- `if total > 0 else 0.0` — avoid division-by-zero error when no messages have been received yet.

```python
m1, m2, m3, m4 = st.columns(4)
m1.metric(label="✅  Processed", value=snap["processed"], ...)
```
- Split the main area into 4 equal columns for the metric cards.
- `st.metric(...)` draws a large number display card with a label.

---

```python
timeline = snap["timeline"]
if len(timeline) >= 2:
    df_tl = pd.DataFrame(timeline).set_index("ts")
    st.line_chart(df_tl[["processed", "failed"]], ...)
```
- Only draw the chart once we have at least 2 data points.
- `pd.DataFrame(timeline)` — converts the list of dictionaries into a table (rows × columns).
- `.set_index("ts")` — use the timestamp column as the row label (X-axis of the chart).
- `st.line_chart(...)` — draws an interactive line chart.

---

```python
logs = snap["logs"]

if not logs:
    st.info("No messages yet. Start the consumer to begin processing.")
else:
    f1, f2, f3 = st.columns([2, 2, 1])
```
- If no logs: show an info message.
- Otherwise: create 3 columns in ratio 2:2:1 for the filter controls.

```python
    filter_level = st.multiselect(
        "Filter by Level",
        options=["SUCCESS", "INFO", "ERROR", "WARNING"],
        default=["SUCCESS", "INFO", "ERROR", "WARNING"],
    )
```
- `st.multiselect(...)` draws a multi-choice dropdown. All levels selected by default.

```python
    df = pd.DataFrame(logs)
    if filter_level:
        df = df[df["level"].isin(filter_level)]
```
- Convert logs list to a pandas DataFrame (table).
- `.isin(filter_level)` — keep only rows where the "level" column value is in the selected list.

```python
    if filter_ref.strip():
        df = df[df["reference_id"].str.contains(filter_ref.strip(), case=False, na=False)]
```
- `.strip()` removes accidental leading/trailing spaces from the search input.
- `.str.contains(...)` filters rows where reference_id contains the typed text (case-insensitive).

```python
    def _badge(level: str) -> str:
        return f'<span class="badge-{level}">{level}</span>'

    df_display["level"] = df_display["level"].apply(_badge)
```
- `_badge(...)` wraps a level string in an HTML `<span>` tag with a CSS class.
- Example: `"ERROR"` becomes `<span class="badge-ERROR">ERROR</span>` → shown as a red badge.
- `.apply(_badge)` calls this function on every row of the "level" column.

```python
    st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
```
- `.to_html(...)` converts the DataFrame into an HTML table string.
- `escape=False` — don't escape the HTML tags in the level column (so badges render correctly).
- `st.write(...)` with `unsafe_allow_html=True` renders the HTML table in the browser.

---

```python
if st.session_state.get("auto_refresh"):
    time.sleep(REFRESH_INTERVAL_SECONDS)
    st.rerun()
```
- If auto-refresh is on: pause for 3 seconds, then re-run the entire script.
- `st.rerun()` is Streamlit's way of triggering a fresh page render.

---

## Summary — How a single message flows through the system

```
1. Kafka sends an XML message to the topic
         ↓
2. pipeline.py → _run_consumer() picks it up
         ↓
3. pipeline.py → _process_message() is called
         ↓
4. xml_converter.py → xml_to_json() converts XML text → JSON text
         ↓
5. xml_converter.py → extract_by_path() finds the referenceId value
         ↓
6. db_handler.py → update_first_record() runs:
       SELECT ROWID from table WHERE reference_id = 'ABC123' AND ROWNUM=1
       UPDATE table SET json_data = '{"root":...}' WHERE ROWID = <found rowid>
         ↓
7. ConsumerState.inc_processed() increments the counter
   ConsumerState.log("SUCCESS", ...) adds a log entry
         ↓
8. app.py reads the snapshot every 3 seconds and refreshes the dashboard
```

---

## Quick Reference — Terms Glossary

| Term | Meaning |
|---|---|
| `def` | Define a reusable function |
| `class` | Blueprint for creating objects with data + functions |
| `self` | Refers to the current object instance |
| `import` | Load an external library/file |
| `try/except` | Handle errors gracefully without crashing |
| `with` | Context manager — auto-cleanup (like auto-closing files/connections) |
| `f"..."` | f-string — embed variable values in text |
| `dict` | Dictionary — key-value pairs like `{"name": "Alice", "age": 30}` |
| `list` | Ordered collection like `[1, 2, 3]` |
| `None` | Python's way of saying "no value" / "empty" |
| `bool` | True or False |
| `thread` | A background task running in parallel |
| `lock` | Prevents two threads from modifying data simultaneously |
| `commit` | Save database changes permanently |
| `rollback` | Undo uncommitted database changes |
| `ROWID` | Oracle's internal unique identifier for each physical row |
| `cursor` | Database "pen" — executes SQL commands |
| `DataFrame` | Pandas table with rows and columns |
| `st.rerun()` | Refresh/redraw the Streamlit dashboard |
| `session_state` | Persistent memory that survives page refreshes |
