#!/usr/bin/env python3

import sys

from dnsmasq import configuration, process_prefixes_to_dnsmasq
from netboxers import netboxers_helpers
from netboxers.models.dnsmasq_dhcp import *


### Main
def main(ctx: dict):
    try:
        # Test if writing is possible of results
        netboxers_helpers.test_write_to_ddo_fh(ctx)
    except FileNotFoundError:
        print(f"Error: could not write to \'{ctx['dnsmasq_dhcp_output_file']}\'", file=sys.stderr)
        return

    if 'dnsmasq_dhcp_output_file' in ctx and ctx['dnsmasq_dhcp_output_file'] is not None:
        print("Netbox to DNSMasq DHCP config")
        process_prefixes_to_dnsmasq.netbox_to_dnsmasq_dhcp_config(ctx)


### Start up
if __name__ == "__main__":
    # initialize
    ctx = netboxers_helpers.get_ctx()
    ctx = configuration.argparsing(ctx)
    ctx = configuration.parse_config(ctx)

    # Checks
    if not configuration.sanity_checks(ctx):
        sys.exit(1)

    # Go time
    main(ctx)