#!/usr/bin/env python3

import sys
import ipaddress

from powerdnsrec import configuration
from netboxers import netboxers_helpers
from netboxers import netboxers_queries
from netboxers.models.dns_zonefile import *


def powerdns_recursor_zonefile(ctx):
    zo = DNS_Zonefile()

    rr = DNS_Resource_Record(
            rr_type = 'SOA',
            rr_name = ctx['powerdns_rec_domain'],
            soa_mname = 'ns.' + ctx['powerdns_rec_domain'],
            soa_rname = 'hostmaster.' + ctx['powerdns_rec_domain'],
            soa_serial = 7,
            soa_refresh = 86400,
            soa_retry = 7200,
            soa_expire = 3600000,
            soa_minimum_ttl = 1800)
    zo.add_rr(rr)


    rr = DNS_Resource_Record(
            rr_type = 'NS',
            rr_name = '@',
            rr_data = 'ns.' + ctx['powerdns_rec_domain'])
    zo.add_rr(rr)


    # Query for prefixes and ranges
    q = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    for prefix_obj in q['results']:

        # Skip non-IPv4
        if prefix_obj['family']['value'] != 4:
            continue

        # TODO
        # Only focus on Home
        if prefix_obj['site']['slug'] != 'home':
            continue

        # Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
        # Extract all IP addresses in the VRF
        ip_addrs_in_vrf = netboxers_queries.get_dhcp_host_dict_from_vrf(ctx, prefix_obj['vrf']['id'])

        # Run through the tupples
        for tupple in ip_addrs_in_vrf:

            # TODO
            # When Device is set to Offline, skip it
            if tupple['ip_addr_obj']['status']['value'] == 'offline':
                print("Device {} with MAC {} and IP address {} is Offline, skipping".format(
                                    tupple['host_iface'],
                                    tupple['mac_address'],
                                    tupple['ip_addr']))
                continue

            # Add the A record for each interface
            rr = DNS_Resource_Record(
                    rr_type = 'A',
                    rr_name = tupple['interface_name'] + "." + tupple['hostname'],
                    rr_data = tupple['ip_addr'])
            zo.add_rr(rr)


            # Check if a mac_address is available
            if 'mac_address' not in tupple or \
                    tupple['mac_address'] is None or \
                    len(tupple['mac_address']) == 0:

                print("No mac address available for",
                        tupple['hostname'],
                        "interface",
                        tupple['interface_name'],
                        "with",
                        tupple['ip_addr'],
                        file=sys.stderr)
                continue

            devices = netboxers_queries.fetch_devices_from_mac_address(ctx, tupple['mac_address'])
            if devices is None:
                print("No device found based on MAC address:", tupple['mac_address'],
                        file=sys.stderr)
                continue

            # Assume only first record to be relevant, as the MAC address is unique.
            device = devices['results'][0]

            # Extract primary IP of device or virtual machine
            if 'primary_ip' in device and 'address' in device['primary_ip']:
                plain_ip_address = device['primary_ip']['address'].split('/')[0]

                # Check: is it equal to the current record?
                if tupple['ip_addr'] == plain_ip_address:

                    # Add CNAME towards primary ip_address holding interface
                    rr = DNS_Resource_Record(
                            rr_type = 'CNAME',
                            rr_name = tupple['hostname'],
                            rr_data = tupple['interface_name'] + "." + tupple['hostname'] + \
                                          "." + \
                                          ctx['powerdns_rec_domain'])
                    zo.add_rr(rr)


    # Inject footer file
    foot = None
    if 'powerdns_rec_zonefile_footer' in ctx and len(ctx['powerdns_rec_zonefile_footer']) > 0:
        f = open(ctx['powerdns_rec_zonefile_footer'], 'r')
        foot = f.read()
        f.close()

    # Write zonefile
    f = open(ctx['powerdns_rec_zonefile'], 'w')

    # Write the zonefile data to file
    f.write(str(zo))
    f.write("\n")

    # Add footer to zonefile
    if foot is not None:
        f.write(foot)

    f.close()


### WORK IN PROGRESS 192.168.x.x only
def powerdns_recursor_zoneing_reverse_lookups(ctx):
    zo = DNS_Zonefile()

    print(ctx['powerdns_rec_zonefile_in_addr'])
    ### ctx['powerdns_rec_zonefile_in_addr']

    #ipam/ip-addresses/
    zone_name = "168.192.in-addr.arpa"

    rr = DNS_Resource_Record(
            rr_type = 'SOA',
            rr_name = zone_name,
            soa_mname = 'ns.' + ctx['powerdns_rec_domain'],
            soa_rname = 'hostmaster.' + ctx['powerdns_rec_domain'],
            soa_serial = 7,
            soa_refresh = 86400,
            soa_retry = 7200,
            soa_expire = 3600000,
            soa_minimum_ttl = 1800)
    zo.add_rr(rr)


    rr = DNS_Resource_Record(
            rr_type = 'NS',
            rr_name = '@',
            rr_data = 'ns.' + ctx['powerdns_rec_domain'])
    zo.add_rr(rr)


    # Query for prefixes and ranges
    q = netboxers_helpers.query_netbox(ctx, "ipam/ip-addresses/")

    for ip_addr_obj in q['results']:
        tupple = {}

        # Skip non-IPv4
        if ip_addr_obj['family']['value'] != 4:
            continue

        ## HACK
        if not ip_addr_obj['address'].startswith('192.168'):
            print(ip_addr_obj['address'], "not in 192.168")
            continue

        # No interface? Skip
        if 'assigned_object' not in ip_addr_obj:
            print("No interface assigned to", ip_addr_obj['address'])
            continue


        # Assemble the tupple
        tupple['ip_addr'] = ip_addr_obj['address']

        if 'device' in ip_addr_obj['assigned_object']:
            tupple['host_name'] = ip_addr_obj['assigned_object']['device']['name']
        elif 'virtual_machine' in ip_addr_obj['assigned_object']:
            tupple['host_name'] = ip_addr_obj['assigned_object']['virtual_machine']['name']

        tupple['interface_name'] = ip_addr_obj['assigned_object']['name']

        ip_addr_interface = ipaddress.IPv4Interface(tupple['ip_addr'])
        tupple['rev_ip_addr'] = ipaddress.ip_address(ip_addr_interface.ip).reverse_pointer


        # RFC compliant domain name
#        rfc_host_name = tupple['host_name'] + "_" + \
#                            tupple['interface_name'] + "." + \
#                            ctx['dhcp_default_domain'])
        rfc_host_name = tupple['interface_name'] + "." + \
                            tupple['host_name'] + "." + \
                            ctx['powerdns_rec_domain']

        rr = DNS_Resource_Record(
                rr_type = 'PTR',
                rr_name = tupple['rev_ip_addr'],
                rr_data = rfc_host_name)
        zo.add_rr(rr)


    # Not assigned must get a special PTR record
    net_vlan66 = ipaddress.ip_network('192.168.1.0/24')
    for ip_addr_obj in q['results']:
        tupple = {}

        # Skip non-IPv4
        if ip_addr_obj['family']['value'] != 4:
            continue

        ## HACK
        if not ip_addr_obj['address'].startswith('192.168'):
            print(ip_addr_obj['address'], "not in 192.168")
            continue

        # No interface? Skip
        if 'assigned_object' in ip_addr_obj:
            print("Interface assigned to", ip_addr_obj['address'])
            if ip_addr_obj['address'] in net_vlan66.hosts():
                print("Interface assigned to", ip_addr_obj['address'], "is part of 192.168.1.0/24")

            continue

#    net4 = ipaddress.ip_network('192.168.1.0/24')
#    for ip_addr_in_net in net4.hosts():
#
#        tupple = {}
#
#        # No interface? Skip
#        if 'assigned_object' not in ip_addr_obj:
#            print("No interface assigned to", ip_addr_obj['address'])
#            continue
#
#        res = next((i for i, item in enumerate(q['results']) if item["address"] == ip_addr_in_net), None)
#
#        if res is None:
#            ip_addr_interface = ipaddress.IPv4Interface(ip_addr_in_net)
#            rev_ip_addr = ipaddress.ip_address(ip_addr_interface.ip).reverse_pointer
#            print(rev_ip_addr)


#        # Assemble the tupple
#        rfc_host_name = tupple['interface_name'] + "." + \
#                            tupple['host_name'] + "." + \
#                            ctx['dhcp_default_domain']
#
#        ip_addr_interface = ipaddress.IPv4Interface(tupple['ip_addr'])
#        tupple['rev_ip_addr'] = ipaddress.ip_address(ip_addr_interface.ip).reverse_pointer
#
#        rr = DNS_Resource_Record(
#                rr_type = 'PTR',
#                rr_name = tupple['rev_ip_addr'],
#                rr_data = rfc_host_name)
#        zo.add_rr(rr)


    # Write zonefile
    f = open(ctx['powerdns_rec_zonefile_in_addr'], 'w')

    # Write the zonefile data to file
    f.write(str(zo))
    f.write("\n")

    f.close()


### Main
def main(ctx):
    if 'powerdns_rec_zonefile' in ctx and ctx['powerdns_rec_zonefile'] is not None:
        print("Netbox to DNS Zonefile")
        powerdns_recursor_zonefile(ctx)

    if 'powerdns_rec_zonefile_in_addr' in ctx and ctx['powerdns_rec_zonefile_in_addr'] is not None:
        print("Netbox to DNS Zonefile for reverse lookups")
        powerdns_recursor_zoneing_reverse_lookups(ctx)


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
