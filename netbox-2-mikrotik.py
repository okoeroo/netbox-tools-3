#!/usr/bin/env python3

import sys

from printer import printer

from netboxers.configuration_mikrotik import argparsing, parse_config, sanity_checks
from netboxers.netboxers_queries import prefill_cache, cache_netbox_query_list, netbox_query_list
from netboxers.netboxers_helpers import get_ctx
from netboxers.models.dnsmasq_dhcp import *

from netboxers.mikrotik import mikrotik_get, mikrotik_patch, mikrotik_put
from netboxers.mikrotik import netbox_vrf_merge_elements, netbox_dhcp_configs, mikrotik_configure
import ipaddress


### Main
def main(ctx):
    vrfs_merged = netbox_vrf_merge_elements(ctx)
    dhcp_configs = netbox_dhcp_configs(ctx, vrfs_merged)

    mikrotik_configure(ctx, dhcp_configs)



### Start up
if __name__ == "__main__":
    # initialize
    ctx = get_ctx()
    ctx = argparsing(ctx)
    ctx = parse_config(ctx)


    # Checks
    if not sanity_checks(ctx):
        sys.exit(1)

    # Fill the cache
#    cached_endpoints = [
##            "dcim/devices/",
##            "dcim/interfaces/",
#            "ipam/ip-addresses/",
#            "ipam/prefixes/",
##            "ipam/vlans/",
#            "ipam/vrfs/",
##            "virtualization/interfaces/",
##            "virtualization/virtual-machines/",
#        ]
#    ctx = prefill_cache(ctx, cached_endpoints)

    # Go time
    main(ctx)
