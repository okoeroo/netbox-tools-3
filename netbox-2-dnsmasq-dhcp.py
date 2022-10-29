#!/usr/bin/env python3

import sys
import ipaddress

from dnsmasq import configuration
from netboxers import netboxers_helpers
from netboxers import netboxers_queries
from netboxers.models.dnsmasq_dhcp import *



# This function will create a DNSMasq formatted DHCP config file from Netbox
## Create DNSMasq DHCP config file by:
## 1. Fetching defaults
## 2. Fetching VRFs, and VRF info.
## 3. Fetch associated default gateway and DNS config
## 4. Fetch (virtual) hosts and its data (IP and MAC)

def netbox_to_dnsmasq_dhcp_config(ctx):
    # Create DNSMasq DHCP config
    dnsmasq_dhcp_config = DNSMasq_DHCP_Config()

    # Fetch header info
    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("dhcp-leasefile", ctx['dnsmasq_dhcp_lease_file']))

    if ctx['dnsmasq_dhcp_authoritive']:
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-authoritative", None))

    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("domain", ctx['dnsmasq_dhcp_default_domain']))


    # Get prefixes
    prefixes = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    if prefixes['count'] == 0:
        print("No prefixes found to complete")

    for prefix_obj in prefixes['results']:
        dnsmasq_dhcp_section = DNSMasq_DHCP_Section()

        # Skip non-IPv4
        if prefix_obj['is_pool'] != True:
            continue

        # Only Active Prefixes
        if prefix_obj['status']['value'] != 'active':
            print("Prefix {} not active, skipping.".format(prefix_obj['prefix']))
            continue


        # Record the DNSMasq_DHCP_Section info
        if prefix_obj['site'] is not None:
            dnsmasq_dhcp_section.set_site(prefix_obj['site']['name'])
        if prefix_obj['role'] is not None:
            dnsmasq_dhcp_section.set_role(prefix_obj['role']['name'])
        if prefix_obj['vlan'] is not None:
            dnsmasq_dhcp_section.set_vlan_id(prefix_obj['vlan']['vid'])
            dnsmasq_dhcp_section.set_vlan_name(prefix_obj['vlan']['display'])
        if prefix_obj['vrf'] is not None:
            dnsmasq_dhcp_section.set_vrf_name(prefix_obj['vrf']['name'])
        if prefix_obj['prefix'] is not None:
            dnsmasq_dhcp_section.set_prefix(prefix_obj['prefix'])


        # Get default gateway from the VRF based on a tag
        default_gateway_ip_addr_obj = netboxers_queries.get_net_default_gateway_from_vrf(ctx, prefix_obj['vrf']['id'])
        if default_gateway_ip_addr_obj is not None:
            default_gateway_ip_addr = \
                ipaddress.ip_address(default_gateway_ip_addr_obj['address'].split("/")[0])

            # Write default gateway
            if default_gateway_ip_addr is not None:
                # Record the default gateway
                dnsmasq_dhcp_section.append_dhcp_option(
                        DNSMasq_DHCP_Option(
                            netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                            "3", default_gateway_ip_addr))


                # Get DNS from the default gateway record
                default_dnsname_ip_addr = netboxers_queries.get_dns_host_from_ip_address(ctx, \
                    default_gateway_ip_addr_obj)

                # Write DNS server
                if default_dnsname_ip_addr is not None:
                    # Record the default gateway
                    ## Recording scope, option and value
                    dnsmasq_dhcp_section.append_dhcp_option(
                            DNSMasq_DHCP_Option(
                                netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                                "6", default_dnsname_ip_addr))

            # Write default NTP server
            if 'dnsmasq_dhcp_default_ntp_server' in ctx and ctx['dnsmasq_dhcp_default_ntp_server'] is not None:
                dnsmasq_dhcp_section.append_dhcp_option(
                        DNSMasq_DHCP_Option(
                            netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                            "42", ctx['dnsmasq_dhcp_default_ntp_server']))

        # Print dhcp-range
        ip_network = ipaddress.ip_network(prefix_obj['prefix'])

        # Record the DHCP range
        dnsmasq_dhcp_section.append_dhcp_range(
                DNSMasq_DHCP_Range(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    ip_network.network_address + int(ctx['dnsmasq_dhcp_host_range_offset_min']),
                    ip_network.network_address + int(ctx['dnsmasq_dhcp_host_range_offset_max']),
                    ip_network.netmask,
                    ctx['dnsmasq_dhcp_default_lease_time_range']))


        # Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
        # Extract all IP addresses in the VRF
        dhcp_host_tuples = netboxers_queries.get_dhcp_host_dict_from_vrf(ctx, prefix_obj['vrf']['id'])

        for tup in dhcp_host_tuples:
            # TODO
            # When Device is set to Offline, skip it
            if tup['ip_addr_obj']['status']['value'] == 'offline':
                print("Device {} with MAC {} and IP address {} is Offline, skipping".format(
                                    tup['host_iface'],
                                    tup['mac_address'],
                                    tup['ip_addr']))
                continue

            # Record the DHCP host
            dnsmasq_dhcp_section.append_dhcp_host(
                    DNSMasq_DHCP_Host(
                        netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                        tup['mac_address'], tup['host_iface'],
                        tup['ip_addr'], ctx['dnsmasq_dhcp_default_lease_time_host']))

        # Record section to config
        dnsmasq_dhcp_config.append_to_dhcp_config_sections(dnsmasq_dhcp_section)


    # Truncate and open file cleanly
    netboxers_helpers.write_to_ddo_fh(ctx, None)

    ## Output DNSMasq Config to file
    netboxers_helpers.write_to_ddo_fh(ctx, str(dnsmasq_dhcp_config))



### Main
def main(ctx: {}):
    if 'dnsmasq_dhcp_output_file' in ctx and ctx['dnsmasq_dhcp_output_file'] is not None:
        print("Netbox to DNSMasq DHCP config")
        netbox_to_dnsmasq_dhcp_config(ctx)


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
