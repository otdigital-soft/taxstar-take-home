from flask import request

from api.errors import malformed_json


def parse_json_body():
    """
    Return (data, error_response).
    error_response is a Flask response tuple when JSON is malformed.
    """
    if request.data:
        data = request.get_json(silent=True)
        if data is None:
            return None, malformed_json()
        if not isinstance(data, dict):
            return None, malformed_json()
        return data, None
    # Empty body → treat as empty object for validators to reject.
    return {}, None
