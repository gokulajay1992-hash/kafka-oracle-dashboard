import json
import xmltodict


def xml_to_json(xml_string: str) -> tuple[str | None, str | None]:
    """
    Convert an XML string to a compact JSON string.

    Returns:
        (json_str, None)        on success
        (None,     error_msg)   on failure
    """
    try:
        parsed = xmltodict.parse(xml_string, force_list=False)
        return json.dumps(parsed, ensure_ascii=False), None
    except Exception as exc:
        return None, str(exc)


def extract_by_path(data: dict, dotted_path: str):
    """
    Traverse a nested dict using a dotted path string.
    Example: extract_by_path(d, "root.header.referenceId")
    Returns the value or raises KeyError / TypeError.
    """
    keys = dotted_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                raise KeyError(f"Key '{key}' not found. Available keys: {list(current.keys())}")
            current = current[key]
        else:
            raise TypeError(
                f"Expected dict at '{key}' but got {type(current).__name__}. "
                f"Check your REFERENCE_ID_PATH in config.py."
            )
    return current
