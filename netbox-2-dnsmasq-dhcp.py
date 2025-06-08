#!/usr/bin/env python3

import sys

from dnsmasq.process_prefixes_to_dnsmasq import netbox_to_dnsmasq_dhcp_config
from dnsmasq.configuration import argparsing, parse_config, sanity_checks
from netboxers.netboxers_queries import prefill_cache
from netboxers.netboxers_helpers import get_ctx, test_write_to_ddo_fh
from netboxers.models.dnsmasq_dhcp import *


### Main
def main(ctx: dict):
    ctx = prefill_cache(ctx)

    try:
        # Test if writing is possible of results
        test_write_to_ddo_fh(ctx)
    except FileNotFoundError:
        print(f"Error: could not write to \'{ctx['dnsmasq_dhcp_output_file']}\'", file=sys.stderr)
        return

    print("Netbox to DNSMasq DHCP config")
    netbox_to_dnsmasq_dhcp_config(ctx)


### Start up
if __name__ == "__main__":
    # initialize
    ctx = get_ctx()
    ctx = argparsing(ctx)
    ctx = parse_config(ctx)

    # Checks
    if not sanity_checks(ctx):
        sys.exit(1)

    # Go time
    main(ctx)