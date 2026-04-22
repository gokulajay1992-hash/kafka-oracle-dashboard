"""
pipeline.py — Kafka consumer + XML→JSON→Oracle pipeline.

This module owns a single module-level ConsumerState object that persists
across Streamlit reruns (Streamlit re-imports the module only once per process).
The consumer runs in a daemon thread so it dies automatically when the app exits.
"""

import json
import threading
import time
from datetime import datetime

from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import NoBrokersAvailable

from config import KAFKA_CONFIG, MAX_LOG_ENTRIES, REFERENCE_ID_PATH
from db_handler import update_first_record
from xml_converter import extract_by_path, xml_to_json


# ---------------------------------------------------------------------------
# Shared state (thread-safe)
# ---------------------------------------------------------------------------

class ConsumerState:
    def __init__(self):
        self._lock = threading.Lock()
        self.running: bool = False
        self.processed: int = 0
        self.failed: int = 0
        self._logs: list[dict] = []
        self._thread: threading.Thread | None = None
        # Per-minute throughput tracking  (timestamp → count)
        self._timeline: list[dict] = []   # [{ts, processed, failed}, ...]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def log(self, level: str, message: str, reference_id: str = "-"):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "reference_id": reference_id,
            "message": message,
        }
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > MAX_LOG_ENTRIES:
                self._logs = self._logs[-MAX_LOG_ENTRIES:]

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    def inc_processed(self):
        with self._lock:
            self.processed += 1
            self._push_timeline()

    def inc_failed(self):
        with self._lock:
            self.failed += 1
            self._push_timeline()

    def _push_timeline(self):
        """Append a snapshot every time a message is counted."""
        self._timeline.append({
            "ts": datetime.now().strftime("%H:%M:%S"),
            "processed": self.processed,
            "failed": self.failed,
        })
        if len(self._timeline) > 300:
            self._timeline = self._timeline[-300:]

    # ------------------------------------------------------------------
    # Read snapshot (for UI)
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running": self.running,
                "processed": self.processed,
                "failed": self.failed,
                "logs": list(reversed(self._logs)),   # newest first
                "timeline": list(self._timeline),
            }

    def reset_counters(self):
        with self._lock:
            self.processed = 0
            self.failed = 0
            self._logs.clear()
            self._timeline.clear()

    # ------------------------------------------------------------------
    # Start / stop
    # ------------------------------------------------------------------
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
        self.log("INFO", f"Consumer started → topic '{KAFKA_CONFIG['topic']}'")

    def stop(self):
        with self._lock:
            if not self.running:
                return
            self.running = False
        self.log("INFO", "Consumer stop requested. Waiting for thread to finish…")


def test_kafka_connection() -> tuple[bool, str]:
    """
    Verify Kafka is reachable and the configured topic exists.
    Returns (True, success_message) or (False, error_message).
    """
    protocol = KAFKA_CONFIG.get("security_protocol", "PLAINTEXT")

    admin_kwargs = {
        "bootstrap_servers": KAFKA_CONFIG["bootstrap_servers"],
        "security_protocol": protocol,
    }

    # Pass SSL fields if applicable
    if protocol in ("SSL", "SASL_SSL"):
        for ssl_key in ("ssl_cafile", "ssl_certfile", "ssl_keyfile", "ssl_password", "ssl_check_hostname"):
            if ssl_key in KAFKA_CONFIG and KAFKA_CONFIG[ssl_key] is not None:
                admin_kwargs[ssl_key] = KAFKA_CONFIG[ssl_key]

    # Pass SASL fields if applicable
    for sasl_key in ("sasl_mechanism", "sasl_plain_username", "sasl_plain_password"):
        if sasl_key in KAFKA_CONFIG and KAFKA_CONFIG[sasl_key] is not None:
            admin_kwargs[sasl_key] = KAFKA_CONFIG[sasl_key]

    try:
        admin = KafkaAdminClient(**admin_kwargs)
        topics = admin.list_topics()
        admin.close()

        topic = KAFKA_CONFIG["topic"]
        if topic in topics:
            return True, f"Connected to Kafka. Topic '{topic}' found. ({len(topics)} total topics on broker)"
        else:
            return False, (
                f"Connected to Kafka broker, but topic '{topic}' was NOT found.\n"
                f"Available topics: {', '.join(sorted(topics)) or '(none)'}"
            )
    except NoBrokersAvailable:
        return False, f"Cannot reach Kafka broker at '{KAFKA_CONFIG['bootstrap_servers']}'. Check host/port and SSL settings."
    except Exception as exc:
        return False, str(exc)


# Module-level singleton — survives Streamlit reruns
state = ConsumerState()


# ---------------------------------------------------------------------------
# Consumer loop
# ---------------------------------------------------------------------------

def _build_kafka_consumer() -> KafkaConsumer:
    import os
    protocol = KAFKA_CONFIG.get("security_protocol", "PLAINTEXT")

    kwargs = {
        "bootstrap_servers": KAFKA_CONFIG["bootstrap_servers"],
        "group_id":          KAFKA_CONFIG["group_id"],
        "auto_offset_reset": KAFKA_CONFIG["auto_offset_reset"],
        "value_deserializer": lambda m: m.decode("utf-8", errors="replace"),
        "consumer_timeout_ms": 1000,
        "security_protocol": protocol,
    }

    # ── SASL_SSL or SASL_PLAINTEXT with Kerberos (GSSAPI) ────────────────────
    if protocol in ("SASL_SSL", "SASL_PLAINTEXT"):
        kwargs["sasl_mechanism"] = KAFKA_CONFIG.get("sasl_mechanism", "GSSAPI")

        if kwargs["sasl_mechanism"] == "GSSAPI":
            # Set Kerberos config file path as environment variable
            krb5_path = KAFKA_CONFIG.get("krb5_conf_path")
            if krb5_path:
                os.environ["KRB5_CONFIG"] = krb5_path

            # Build JAAS config string for Kerberos keytab login
            keytab   = KAFKA_CONFIG.get("sasl_kerberos_keytab", "")
            principal = KAFKA_CONFIG.get("sasl_kerberos_principal", "")
            kwargs["sasl_kerberos_service_name"] = KAFKA_CONFIG.get("sasl_kerberos_service_name", "kafka")
            kwargs["sasl_jaas_config"] = (
                f'com.sun.security.auth.module.Krb5LoginModule required '
                f'useKeyTab=true '
                f'storeKey=true '
                f'keyTab="{keytab}" '
                f'principal="{principal}";'
            )

        # Plain username/password (PLAIN / SCRAM)
        for sasl_key in ("sasl_plain_username", "sasl_plain_password"):
            if sasl_key in KAFKA_CONFIG and KAFKA_CONFIG[sasl_key] is not None:
                kwargs[sasl_key] = KAFKA_CONFIG[sasl_key]

    # ── SSL truststore (SASL_SSL or plain SSL) ────────────────────────────────
    if protocol in ("SSL", "SASL_SSL"):
        if KAFKA_CONFIG.get("ssl_truststore_location"):
            kwargs["ssl_cafile"]   = KAFKA_CONFIG["ssl_truststore_location"]
        if KAFKA_CONFIG.get("ssl_truststore_password"):
            kwargs["ssl_password"] = KAFKA_CONFIG["ssl_truststore_password"]
        # Optional client cert fields
        for ssl_key in ("ssl_certfile", "ssl_keyfile", "ssl_check_hostname"):
            if ssl_key in KAFKA_CONFIG and KAFKA_CONFIG[ssl_key] is not None:
                kwargs[ssl_key] = KAFKA_CONFIG[ssl_key]

    return KafkaConsumer(KAFKA_CONFIG["topic"], **kwargs)


def _run_consumer(s: ConsumerState):
    """Main consumer loop — runs in its own thread."""
    try:
        consumer = _build_kafka_consumer()
    except NoBrokersAvailable as exc:
        s.log("ERROR", f"Cannot reach Kafka brokers: {exc}")
        with s._lock:
            s.running = False
        return
    except Exception as exc:
        s.log("ERROR", f"Kafka consumer init failed: {exc}")
        with s._lock:
            s.running = False
        return

    s.log("INFO", "Kafka consumer connected and listening…")

    try:
        while s.running:
            try:
                for msg in consumer:
                    if not s.running:
                        break
                    _process_message(msg.value, s)
            except StopIteration:
                # consumer_timeout_ms expired — no messages, loop again
                pass
    finally:
        consumer.close()
        with s._lock:
            s.running = False
        s.log("INFO", "Kafka consumer closed.")


# ---------------------------------------------------------------------------
# Per-message processing
# ---------------------------------------------------------------------------

def _process_message(raw: str, s: ConsumerState):
    # 1 — XML → JSON
    json_str, err = xml_to_json(raw)
    if err:
        s.inc_failed()
        s.log("ERROR", f"XML parse failed: {err}")
        return

    # 2 — Extract reference_id
    try:
        parsed = json.loads(json_str)
        reference_id = str(extract_by_path(parsed, REFERENCE_ID_PATH))
    except (KeyError, TypeError, ValueError) as exc:
        s.inc_failed()
        s.log(
            "ERROR",
            f"reference_id extraction failed ({exc}). "
            f"Check REFERENCE_ID_PATH in config.py.",
        )
        return

    # 3 — Persist to Oracle
    ok, msg = update_first_record(reference_id, json_str)
    if ok:
        s.inc_processed()
        s.log("SUCCESS", msg, reference_id)
    else:
        s.inc_failed()
        s.log("ERROR", f"DB update failed: {msg}", reference_id)
