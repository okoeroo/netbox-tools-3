#!/usr/bin/env python3

import sys

from netboxers.configuration_mikrotik import argparsing, parse_config, sanity_checks
from netboxers.netboxers_queries import prefill_cache
from netboxers.netboxers_helpers import get_ctx
from netboxers.models.dnsmasq_dhcp import *



### Main
def main(ctx):
    ctx = prefill_cache(ctx)

    print("Doei")
    sys.exit(0)



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
