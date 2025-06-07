#!/usr/bin/env python3

import sys

from powerdnsrec.configuration import argparsing, parse_config, sanity_checks
from netboxers.netboxers_helpers import get_ctx
from powerdnsrec.dnsprocessing import powerdns_recursor_zonefile, \
                                      write_zonefile, \
                                      read_zonefile_footer_file, \
                                      powerdns_recursor_zoneing_reverse_lookups


### Main
def main(ctx):
    # if ctx.get('powerdns_rec_zonefile'):
    #     print("Netbox to DNS Zonefile")
    #     try:
    #         zo = powerdns_recursor_zonefile(ctx)
    #         footer = read_zonefile_footer_file(ctx)
    #         write_zonefile(ctx, zo, footer)
            
    #     except Exception as err:
    #         print(f"Error: {err}")
    #         sys.exit(1)

    if ctx.get('powerdns_rec_zonefile_in_addr'):
        print("Netbox to DNS Zonefile for reverse lookups")
        try:
            powerdns_recursor_zoneing_reverse_lookups(ctx)
        except Exception as err:
            print(f"Error: {err}")
            sys.exit(1)


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
