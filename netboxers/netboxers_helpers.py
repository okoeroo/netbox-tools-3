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


def test_write_to_ddo_fh(ctx: dict):
    # Truncate file
    if ctx['dnsmasq_dhcp_output_file'] is not None:
        open(ctx['dnsmasq_dhcp_output_file'], 'w').close()
        return


def write_to_ddo_fh(ctx: dict, s: str | None):
    # Truncate file
    if s is None and ctx['dnsmasq_dhcp_output_file'] is not None:
        open(ctx['dnsmasq_dhcp_output_file'], 'w').close()
        return

    # Print or write
    if ctx['dnsmasq_dhcp_output_file'] is None:
        print(s)
    else:
        with open(ctx['dnsmasq_dhcp_output_file'], 'a') as the_file:
            if s is None:
                the_file.write(os.linesep)
            else:
                the_file.write(s + os.linesep)


def get_ctx():
    ctx = {}
    return ctx
