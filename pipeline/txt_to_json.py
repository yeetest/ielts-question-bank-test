"""
txt_to_json.py
Usage: python txt_to_json.py yourfile.txt
Output: yourfile.json (rebuilt from flat key=value txt)
Edit the .txt file, then run this to sync changes back to JSON.
"""

import json
import sys
import re
from pathlib import Path


def set_nested(obj, keys, value):
    """Sets a value in a nested dict/list structure given a list of keys."""
    for key in keys[:-1]:
        if isinstance(key, int):
            # obj must be a list
            while len(obj) <= key:
                obj.append(None)
            # determine next container type from next key
            next_key = keys[keys.index(key) + 1]
            if obj[key] is None:
                obj[key] = [] if isinstance(next_key, int) else {}
            obj = obj[key]
        else:
            # obj must be a dict
            next_key = keys[keys.index(key) + 1]
            if key not in obj or obj[key] is None:
                obj[key] = [] if isinstance(next_key, int) else {}
            obj = obj[key]

    last = keys[-1]
    if isinstance(last, int):
        while len(obj) <= last:
            obj.append(None)
        obj[last] = value
    else:
        obj[last] = value


def parse_key(raw_key):
    """Converts dot-notation string like 'a.b[2].c' into a list of keys ['a','b',2,'c']."""
    parts = []
    for segment in re.split(r'\.', raw_key):
        match = re.match(r'^(.*?)\[(\d+)\]$', segment)
        if match:
            if match.group(1):
                parts.append(match.group(1))
            parts.append(int(match.group(2)))
        else:
            if segment:
                parts.append(segment)
    return parts


def parse_value(raw_value):
    """Tries to restore original type: int, float, bool, null, or string."""
    v = raw_value.strip()
    if v == "None" or v == "null":
        return None
    if v == "True" or v == "true":
        return True
    if v == "False" or v == "false":
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v  # stays as string


def main():
    if len(sys.argv) < 2:
        print("Usage: python txt_to_json.py yourfile.txt")
        sys.exit(1)

    txt_path = Path(sys.argv[1])
    json_path = txt_path.with_suffix(".json")

    # Peek at first non-comment line to decide if root is list or dict
    root = None
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            raw_key = line.partition("=")[0].strip()
            keys = parse_key(raw_key)
            root = [] if isinstance(keys[0], int) else {}
            break

    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):  # skip blanks and comments
                continue
            if "=" not in line:
                print(f"Skipping unrecognized line: {line}")
                continue
            raw_key, _, raw_value = line.partition("=")
            keys = parse_key(raw_key.strip())
            value = parse_value(raw_value)
            set_nested(root, keys, value)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)

    print(f"Synced to {json_path}")


if __name__ == "__main__":
    main()
