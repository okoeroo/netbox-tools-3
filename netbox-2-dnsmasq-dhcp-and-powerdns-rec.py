#!/usr/bin/env python3

import sys

from dnsmasq.process_prefixes_to_dnsmasq import netbox_to_dnsmasq_dhcp_config
from dnsmasq.configuration import argparsing, parse_config, sanity_checks
from netboxers.netboxers_queries import prefill_cache
from netboxers.netboxers_helpers import get_ctx, test_write_to_ddo_fh
from netboxers.models.dnsmasq_dhcp import *

# from powerdnsrec.configuration import argparsing, parse_config, sanity_checks
from powerdnsrec.dnsprocessing import powerdns_recursor_zonefile, \
                                      write_zonefile, \
                                      read_zonefile_footer_file, \
                                      powerdns_recursor_zoneing_reverse_lookups


### Main
def main(ctx):
    ctx = prefill_cache(ctx)

    #### DNSMasq DHCP
    try:
        # Test if writing is possible of results
        test_write_to_ddo_fh(ctx)
    except FileNotFoundError:
        print(f"Error: could not write to \'{ctx['dnsmasq_dhcp_output_file']}\'", file=sys.stderr)
        return

    print("Netbox to DNSMasq DHCP config")
    netbox_to_dnsmasq_dhcp_config(ctx)
    

    #### PowerDNS Recursor
    if ctx.get('powerdns_rec_zonefile'):
        print("Netbox to DNS Zonefile")
        zo = powerdns_recursor_zonefile(ctx)
        footer = read_zonefile_footer_file(ctx)
        write_zonefile(ctx, zo, footer)

    if ctx.get('powerdns_rec_zonefile_in_addr'):
        print("Netbox to DNS Zonefile for reverse lookups")
        powerdns_recursor_zoneing_reverse_lookups(ctx)



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
