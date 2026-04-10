# ============================================================
#  EDIT THIS FILE to match your environment before running
# ============================================================
#
#  Your Pega DB JDBC URL format (Java reference — do NOT paste this into code):
#    jdbc:oracle:thin:@<host>:<port>/<service_name>
#  Example:
#    jdbc:oracle:thin:@pega-db.company.com:1521/pegadb
#
#  Extract the 3 parts from your JDBC URL and fill in below:
#    host         → everything between @ and :
#    port         → number after the colon (usually 1521)
#    service_name → everything after the last /  (pegadb in your case)
# ============================================================

KAFKA_CONFIG = {
    "bootstrap_servers": "localhost:9093",      # SSL typically uses port 9093
    "topic": "your-topic-name",
    "group_id": "kafka-oracle-dashboard-group",
    "auto_offset_reset": "latest",              # "latest" or "earliest"

    # ── SSL Security Protocol ────────────────────────────────────────────────
    "security_protocol": "SSL",

    # Path to the CA certificate that signed the Kafka broker's certificate.
    "ssl_cafile": "/path/to/ca-cert.pem",

    # Client certificate — proves YOUR identity to the Kafka broker (mutual TLS).
    # Set to None if the broker does not require client authentication.
    "ssl_certfile": "/path/to/client-cert.pem",

    # Private key paired with the client certificate above.
    "ssl_keyfile": "/path/to/client-key.pem",

    # Password for the private key file. Set to None if key has no password.
    "ssl_password": None,

    # Verify broker hostname matches its certificate (recommended: True).
    "ssl_check_hostname": True,

    # ── SASL over SSL (uncomment if broker also requires username + password)
    # "security_protocol": "SASL_SSL",
    # "sasl_mechanism": "PLAIN",
    # "sasl_plain_username": "your-username",
    # "sasl_plain_password": "your-password",
}

# ── Pega Oracle Database ─────────────────────────────────────────────────────
#
# Your Pega JDBC URL:  jdbc:oracle:thin:@<host>:<port>/<service_name>
#
# Fill in the 3 values extracted from your JDBC URL:
ORACLE_CONFIG = {
    "host":         "your-pega-db-host",        # ← hostname/IP from your JDBC URL
    "port":         1521,                        # ← port from your JDBC URL (usually 1521)
    "service_name": "pegadb",                   # ← service name from your JDBC URL

    "username": "your_db_user",
    "password": "your_db_password",

    # ── Target table (custom-managed, not a Pega system table) ───────────────
    "table_name":            "your_table_name",
    "reference_id_column":   "reference_id",    # column used to find the row
    "json_data_column":      "json_data",       # empty column that receives JSON

    # ── Oracle connection security ────────────────────────────────────────────
    # "tcp"  = plain connection  |  "tcps" = TLS-encrypted (requires wallet/cert)
    "protocol":         "tcp",                  # change to "tcps" if Pega DB uses TLS

    # Oracle Wallet (only needed when protocol = "tcps")
    # Set to None if not using wallet-based TLS
    "wallet_location":  None,                   # e.g. "/path/to/wallet"
    "wallet_password":  None,
}

# Dotted path to the reference_id field inside your XML → dict structure.
# Example XML:  <root><header><referenceId>ABC</referenceId></header></root>
# → PATH = "root.header.referenceId"
REFERENCE_ID_PATH = "root.header.referenceId"

# Dashboard auto-refresh interval in seconds
REFRESH_INTERVAL_SECONDS = 3

# Maximum log entries kept in memory
MAX_LOG_ENTRIES = 500
