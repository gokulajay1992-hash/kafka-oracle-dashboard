# ============================================================
#  EDIT THIS FILE to match your environment before running
#  Set ENVIRONMENT to "dev", "qa", "uat", or "prod"
# ============================================================

ENVIRONMENT = "dev"   # ← Change this to switch environments: "dev" | "qa" | "uat" | "prod"

# ── Environment-specific Kafka broker settings ────────────────────────────────
#
#  Non-prod (dev/qa/uat) → port 9092
#  Prod                  → port 9093
#
_KAFKA_BROKERS = {
    "dev": [
        "ch3dr1017045.express-scripts.com:9092",
        "ch3dr1017046.express-scripts.com:9092",
        "ch3dr1017047.express-scripts.com:9092",
    ],
    "qa": [
        "ch3dr1017045.express-scripts.com:9092",
        "ch3dr1017046.express-scripts.com:9092",
        "ch3dr1017047.express-scripts.com:9092",
    ],
    "uat": [
        "ch3dr1017045.express-scripts.com:9092",
        "ch3dr1017046.express-scripts.com:9092",
        "ch3dr1017047.express-scripts.com:9092",
    ],
    "prod": [
        "ch3dr1017045.express-scripts.com:9093",   # prod uses 9093
        "ch3dr1017046.express-scripts.com:9093",
        "ch3dr1017047.express-scripts.com:9093",
    ],
}

# ── Environment-specific SSL / Kerberos file paths ────────────────────────────
#
#  Each environment has its own set of security files.
#  Update the paths below to point to where these files live on your machine.
#
_KAFKA_SECURITY = {
    "dev": {
        "truststore":   "kafka/dev/devpkafka.server.truststore.jks",
        "keytab":       "kafka/dev/DKFKpocepa.keytab",
        "jaas_conf":    "kafka/dev/jaas.conf",
        "krb5_conf":    "kafka/dev/krb5.conf",
        "principal":    "DKFKpocepa@ACCOUNTS.ROOT.CORP",
        "truststore_password": "DevpKafstsp@Ahkni9790#",
        "group_id":     "APP_EPAPointOfCare_DEV",
    },
    "qa": {
        "truststore":   "kafka/qa/qapkafka.server.truststore.jks",
        "keytab":       "kafka/qa/DKFKpocepa.keytab",
        "jaas_conf":    "kafka/qa/jaas.conf",
        "krb5_conf":    "kafka/qa/krb5.conf",
        "principal":    "DKFKpocepa@ACCOUNTS.ROOT.CORP",
        "truststore_password": "your-qa-truststore-password",
        "group_id":     "APP_EPAPointOfCare_QA",
    },
    "uat": {
        "truststore":   "kafka/uat/uatpkafka.server.truststore.jks",
        "keytab":       "kafka/uat/DKFKpocepa.keytab",
        "jaas_conf":    "kafka/uat/jaas.conf",
        "krb5_conf":    "kafka/uat/krb5.conf",
        "principal":    "DKFKpocepa@ACCOUNTS.ROOT.CORP",
        "truststore_password": "your-uat-truststore-password",
        "group_id":     "APP_EPAPointOfCare_UAT",
    },
    "prod": {
        "truststore":   "kafka/prod/prodpkafka.server.truststore.jks",
        "keytab":       "kafka/prod/DKFKpocepa.keytab",
        "jaas_conf":    "kafka/prod/jaas.conf",
        "krb5_conf":    "kafka/prod/krb5.conf",
        "principal":    "DKFKpocepa@ACCOUNTS.ROOT.CORP",
        "truststore_password": "your-prod-truststore-password",
        "group_id":     "APP_EPAPointOfCare_PROD",
    },
}

# ── Kafka topics ──────────────────────────────────────────────────────────────
KAFKA_TOPICS = {
    "initiation_request": "TP.ONEPA.EPACREATERASEREQUEST",
    "pars_request":       "TP.ONEPA.EPACREATECASE",      # ← confirm exact name with team
}

# ── Build the active KAFKA_CONFIG from the selected environment ───────────────
_env_brokers  = _KAFKA_BROKERS[ENVIRONMENT]
_env_security = _KAFKA_SECURITY[ENVIRONMENT]

KAFKA_CONFIG = {
    "bootstrap_servers": ",".join(_env_brokers),
    "topic":             KAFKA_TOPICS["initiation_request"],  # ← change to whichever topic to consume
    "group_id":          _env_security["group_id"],
    "auto_offset_reset": "latest",                            # "latest" or "earliest"

    # ── Security Protocol ──────────────────────────────────────────────────────
    # Non-prod: SASL_PLAINTEXT (port 9092)
    # Prod:     SASL_SSL       (port 9093)
    "security_protocol": "SASL_SSL" if ENVIRONMENT == "prod" else "SASL_PLAINTEXT",

    # ── SASL Kerberos (GSSAPI) ─────────────────────────────────────────────────
    "sasl_mechanism":    "GSSAPI",
    "sasl_kerberos_service_name": "cdkafka",

    # ── Kerberos / SSL file paths (resolved from environment above) ────────────
    "ssl_truststore_location": _env_security["truststore"],
    "ssl_truststore_password": _env_security["truststore_password"],
    "sasl_kerberos_keytab":    _env_security["keytab"],
    "sasl_kerberos_principal": _env_security["principal"],
    "sasl_jaas_config_path":   _env_security["jaas_conf"],
    "krb5_conf_path":          _env_security["krb5_conf"],
}

# ── Pega Oracle Database ──────────────────────────────────────────────────────
#
#  Your Pega JDBC URL:  jdbc:oracle:thin:@<host>:<port>/<service_name>
#  Extract the 3 parts and fill in below:
#
ORACLE_CONFIG = {
    "host":         "your-pega-db-host",        # ← hostname/IP from your JDBC URL
    "port":         1521,                        # ← port (usually 1521)
    "service_name": "pegadb",                   # ← service name from JDBC URL

    "username": "your_db_user",
    "password": "your_db_password",

    # ── Target table ───────────────────────────────────────────────────────────
    "table_name":           "your_table_name",
    "reference_id_column":  "reference_id",     # column used to find the row
    "json_data_column":     "json_data",        # empty column that receives JSON

    # ── Oracle connection security ─────────────────────────────────────────────
    # "tcp"  = plain  |  "tcps" = TLS (requires wallet)
    "protocol":        "tcp",
    "wallet_location": None,
    "wallet_password": None,
}

# ── XML reference ID path ─────────────────────────────────────────────────────
# Dotted path to the reference ID inside your XML structure.
# Example: <root><header><referenceId>ABC</referenceId></header></root>
# → REFERENCE_ID_PATH = "root.header.referenceId"
REFERENCE_ID_PATH = "root.header.referenceId"

# ── Maximum log entries kept in memory ────────────────────────────────────────
MAX_LOG_ENTRIES = 500
