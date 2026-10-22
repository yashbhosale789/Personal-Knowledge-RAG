import json
import re


def parse_json_reply(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise json.JSONDecodeError("no JSON object in reply", raw, 0)
    return json.loads(match.group(0))


if __name__ == "__main__":
    assert parse_json_reply('```json\n{"grounded": true}\n```') == {
        "grounded": True
    }  # nosec B101
    assert parse_json_reply('Sure: {"a": 1} done') == {"a": 1}  # nosec B101
