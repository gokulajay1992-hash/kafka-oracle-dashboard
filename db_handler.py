import oracledb
from config import ORACLE_CONFIG


def _get_dsn() -> str:
    cfg = ORACLE_CONFIG
    return f"{cfg['host']}:{cfg['port']}/{cfg['service_name']}"


def get_connection():
    """Return a new Oracle connection (thin mode — no Oracle Client required).

    Supports:
      - Plain TCP  (protocol = "tcp",  encryption_mode = "disable")
      - Encrypted  (protocol = "tcp",  encryption_mode = "requested"/"required")
      - TCPS/TLS   (protocol = "tcps", with optional wallet)
    """
    connect_params = oracledb.ConnectParams(
        host=ORACLE_CONFIG["host"],
        port=ORACLE_CONFIG["port"],
        service_name=ORACLE_CONFIG["service_name"],
        user=ORACLE_CONFIG["username"],
        password=ORACLE_CONFIG["password"],
        protocol=ORACLE_CONFIG.get("protocol", "tcp"),
    )

    # Apply wallet settings if TCPS and wallet_location is provided
    wallet_location = ORACLE_CONFIG.get("wallet_location")
    if wallet_location:
        connect_params.wallet_location = wallet_location
        wallet_password = ORACLE_CONFIG.get("wallet_password")
        if wallet_password:
            connect_params.wallet_password = wallet_password

    return oracledb.connect(params=connect_params)


def test_connection() -> tuple[bool, str]:
    """Smoke-test the Oracle connection. Returns (ok, message)."""
    try:
        conn = get_connection()
        conn.close()
        return True, "Oracle connection successful."
    except Exception as exc:
        return False, str(exc)


def update_first_record(reference_id: str, json_data: str) -> tuple[bool, str]:
    """
    Find the first row whose `reference_id_column` matches *reference_id*
    (ordered by ROWID — i.e. insertion order) and write *json_data* into
    the `json_data_column`.

    Returns:
        (True,  "Updated")          — row found and updated
        (False, "No record found")  — no matching row
        (False, "<error message>")  — DB error
    """
    table = ORACLE_CONFIG["table_name"]
    ref_col = ORACLE_CONFIG["reference_id_column"]
    json_col = ORACLE_CONFIG["json_data_column"]

    # Use ROWID to pin the exact first row even when duplicates exist.
    select_sql = (
        f"SELECT ROWID FROM {table} "
        f"WHERE {ref_col} = :ref_id "
        f"AND ROWNUM = 1 "
        f"ORDER BY ROWID"
    )
    update_sql = (
        f"UPDATE {table} SET {json_col} = :json_data "
        f"WHERE ROWID = :row_id"
    )

    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(select_sql, ref_id=reference_id)
            row = cur.fetchone()

            if not row:
                return False, f"No record found for reference_id '{reference_id}'"

            row_id = row[0]
            cur.execute(update_sql, json_data=json_data, row_id=row_id)
            conn.commit()
            return True, f"Updated row for reference_id '{reference_id}'"
        except Exception as exc:
            conn.rollback()
            return False, str(exc)
        finally:
            conn.close()
    except Exception as exc:
        return False, f"Connection error: {exc}"
