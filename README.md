# Kafka → Oracle/Pega Pipeline Dashboard

A real-time Streamlit dashboard that reads XML messages from a Kafka topic, converts them to JSON, and saves them to an Oracle/Pega database.

---

## What it does

- Connects to a **Kafka topic** and reads messages in real time (SSL supported)
- Converts incoming **XML messages to JSON**
- Saves the JSON to an **Oracle/Pega database** using a reference ID
- Handles **duplicate reference IDs** — always updates the first matching record
- Displays **live metrics** — processed, failed, success rate, throughput chart and message logs

---

## Project Structure

```
kafka_oracle_dashboard/
├── app.py                  # Streamlit dashboard (entry point)
├── pipeline.py             # Kafka consumer + background thread
├── db_handler.py           # Oracle DB connection and update logic
├── xml_converter.py        # XML → JSON converter
├── config.py               # All settings (fill this in before running)
├── requirements.txt        # Python dependencies
├── DOCUMENTATION.md        # Full line-by-line code documentation
└── README.md               # This file
```

---

## Prerequisites

- Python 3.11 or higher
- Access to a Kafka broker
- Access to an Oracle / Pega database

---

## Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/gokulajay1992-hash/kafka-oracle-dashboard.git
cd kafka-oracle-dashboard
```

### Step 2 — Install dependencies

**Standard (if Python is on PATH):**
```bash
pip install -r requirements.txt
```

**If `pip` is not recognized (Windows PATH issue):**
```powershell
C:\Users\<your-username>\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
```

Replace `<your-username>` with your Windows username. Example:
```powershell
C:\Users\em6676\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
```

**Fix PATH permanently (run once in PowerShell, then restart terminal):**
```powershell
[System.Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Users\em6676\AppData\Local\Programs\Python\Python313;C:\Users\em6676\AppData\Local\Programs\Python\Python313\Scripts", "User")
```

After restarting the terminal, `pip` and `python` will work normally.

---

## Configuration

Open `config.py` and fill in your details:

### Kafka
```python
KAFKA_CONFIG = {
    "bootstrap_servers": "your-kafka-broker:9093",
    "topic": "your-topic-name",
    "ssl_cafile": "/path/to/ca-cert.pem",
    "ssl_certfile": "/path/to/client-cert.pem",
    "ssl_keyfile": "/path/to/client-key.pem",
}
```

### Oracle / Pega DB
```python
# Extract from your JDBC URL:  jdbc:oracle:thin:@<host>:<port>/<service_name>
ORACLE_CONFIG = {
    "host":         "your-pega-db-host",
    "port":         1521,
    "service_name": "pegadb",
    "username":     "your_db_user",
    "password":     "your_db_password",
    "table_name":   "your_table_name",
}
```

### Reference ID Path
```python
# Dotted path to the reference ID inside your XML structure
# Example XML: <root><header><referenceId>ABC</referenceId></header></root>
REFERENCE_ID_PATH = "root.header.referenceId"
```

---

## Running the App

**Standard:**
```bash
streamlit run app.py
```

**If streamlit is not on PATH (Windows):**
```powershell
C:\Users\em6676\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run app.py
```

The dashboard opens automatically at `http://localhost:8501`

---

## Running in IntelliJ IDEA

1. Install the **Python plugin** — File → Settings → Plugins → search `Python`
2. Set interpreter — File → Project Structure → SDKs → Add Python SDK → System Interpreter → browse to `python.exe`
3. Open terminal (`Alt+F12`) and run:
```powershell
C:\Users\em6676\AppData\Local\Programs\Python\Python313\python.exe -m pip install -r requirements.txt
C:\Users\em6676\AppData\Local\Programs\Python\Python313\python.exe -m streamlit run app.py
```

---

## Dashboard Features

| Feature | Description |
|---|---|
| Live metrics | Processed, Failed, Total, Success Rate cards |
| Throughput chart | Line chart of processed vs failed over time |
| Message logs | Filterable table by log level and reference ID |
| Connection tests | Test Oracle and Kafka connections from the sidebar |
| Start / Stop | Control the Kafka consumer from the sidebar |
| Auto refresh | Dashboard updates every 1 second automatically |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.37.0 | Dashboard UI |
| `kafka-python` | ≥ 2.0.2 | Kafka consumer |
| `xmltodict` | ≥ 0.13.0 | XML → JSON conversion |
| `oracledb` | ≥ 2.3.0 | Oracle DB connection (no Oracle Client needed) |
| `pandas` | ≥ 2.0.0 | Log table and chart data |

---

## Pushing Updates to GitHub

After making any code changes:

```bash
git add .
git commit -m "describe your change"
git push
```
