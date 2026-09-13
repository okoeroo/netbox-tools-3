#!/usr/bin/env python3

import sys
import json

from netboxers.configuration_mikrotik import argparsing, parse_config, sanity_checks
from netboxers.netboxers_queries import prefill_cache, cache_netbox_query_list, netbox_query_list
from netboxers.netboxers_helpers import get_ctx
from netboxers.models.dnsmasq_dhcp import *

from netboxers.mikrotik import mikrotik_get, mikrotik_patch, mikrotik_put
from netboxers.mikrotik import mikrotik_pool_netbox_ranges_sync, netbox_get_target_router_device, netbox_get_ip_addresses_with_tag
import ipaddress


### Main
def main(ctx):
#    j_mikro_ip_addrs = mikrotik_get(ctx, "/ip/address")
#    print(j_mikro_ip_addrs)
#
#    # Sync Mikrotik Pools with Netbox ranges
#    mikrotik_pool_netbox_ranges_sync(ctx)

    target_router = netbox_get_target_router_device(ctx)
    print(json.dumps(target_router, indent=2, default=str))


    print(json.dumps(netbox_get_ip_addresses_with_tag(ctx, "net_default_gateway"), indent=2, default=str))
    print(json.dumps(netbox_get_ip_addresses_with_tag(ctx, "net_default_ntp"), indent=2, default=str))
    print(json.dumps(netbox_get_ip_addresses_with_tag(ctx, "net_default_dns"), indent=2, default=str))



# pseudo
"""




"""


### Start up
if __name__ == "__main__":
    # initialize
    ctx = get_ctx()
    ctx = argparsing(ctx)
    ctx = parse_config(ctx)

    print(ctx)

    # Checks
    if not sanity_checks(ctx):
        sys.exit(1)

    # Fill the cache
    cached_endpoints = [
#            "dcim/devices/",
#            "dcim/interfaces/",
            "ipam/ip-addresses/",
#            "ipam/prefixes/",
#            "ipam/vlans/",
#            "ipam/vrfs/",
#            "virtualization/interfaces/",
#            "virtualization/virtual-machines/",
        ]
    ctx = prefill_cache(ctx, cached_endpoints)

    # Go time
    main(ctx)
