import json


def printer(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))
