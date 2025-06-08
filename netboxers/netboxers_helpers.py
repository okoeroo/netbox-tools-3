#!/usr/bin/env python3

import os
import re


# All non-alfanum, replace with underscore and lowercase it
# Used to create a interface + device name combo.
def sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '_', s).lower()


def make_host_iface_name(dev_name: str, if_name: str) -> str:
    return f"{sanitize(dev_name)}_{sanitize(if_name)}"


def make_iface_dot_host_name(dev_name: str, if_name: str) -> str:
    return f"{sanitize(if_name)}.{sanitize(dev_name)}"


def write_data_to_file(filepath: str | None, s: str) -> None:
    # No file, print only
    if filepath is None:
        print(s)
        return

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(s)


def get_ctx():
    ctx = {}
    return ctx
