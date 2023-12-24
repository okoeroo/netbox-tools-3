#!/usr/bin/env python3

import ipaddress
import sys

from dnsmasq import configuration
from netboxers import netboxers_helpers, netboxers_queries
from netboxers.models.dnsmasq_dhcp import *


def netbox_generate_dnsmasq_dhcp_section_header_info(prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
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

    return dnsmasq_dhcp_section


# Get default gateway for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_gateway(ctx, prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
    # Check if there is a specific prefix with gateway in the config file
    if 'prefixes' in ctx and \
        prefix_obj['prefix'] in ctx['prefixes'] and \
        'gateway' in ctx['prefixes'][prefix_obj['prefix']]:

        # Record the default gateway
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "3", ctx['prefixes'][prefix_obj['prefix']]['gateway']))
        return dnsmasq_dhcp_section

    ## Resort to old behavior: Get default gateway from the VRF based on a tag
    default_gateway_ip_addr_obj = netboxers_queries.get_net_default_gateway_from_vrf(ctx, prefix_obj['vrf']['id'])
    if default_gateway_ip_addr_obj is None:
        return None

    # Cut and split cidr to addr
    default_gateway_ip_addr = \
        ipaddress.ip_address(default_gateway_ip_addr_obj['address'].split("/")[0])

    # Write default gateway
    if default_gateway_ip_addr is not None:
        # Record the default gateway
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "3", default_gateway_ip_addr))

    return dnsmasq_dhcp_section


# Get DNS server configuration for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_dns(ctx, prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
    # Override from config or args, or fetch the config from netbox
    if 'dnsmasq_dhcp_override_dns_server' in ctx and ctx['dnsmasq_dhcp_override_dns_server'] is not None:
        default_dnsname_ip_addr = ctx['dnsmasq_dhcp_override_dns_server']

        # Record the DNS server
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "6", default_dnsname_ip_addr))

        return dnsmasq_dhcp_section

    # Check if there is a specific prefix with dns in the config file for its prefix
    if 'prefixes' in ctx and prefix_obj['prefix'] in ctx['prefixes'] and \
        'dns' in ctx['prefixes'][prefix_obj['prefix']]:

        # Record the DNS server
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "6", ctx['prefixes'][prefix_obj['prefix']]['dns']))

        return dnsmasq_dhcp_section

    ### Resort to the old behavior, fetch the gateway address, and from the
    ### gateway address fetch its associated DNS server
    default_gateway_ip_addr_obj = netboxers_queries.get_net_default_gateway_from_vrf(ctx, prefix_obj['vrf']['id'])
    if default_gateway_ip_addr_obj is None:
        return None

    # Cut and split cidr to addr
    default_gateway_ip_addr = \
        ipaddress.ip_address(default_gateway_ip_addr_obj['address'].split("/")[0])

    # Write DNS server based on gateway information
    if default_gateway_ip_addr is not None:
        # Get DNS from the default gateway record
        default_dnsname_ip_addr = netboxers_queries.get_dns_host_from_ip_address(ctx, \
            default_gateway_ip_addr_obj)

        # Write DNS server
        if default_dnsname_ip_addr is not None:
            # Record the DNS server
            ## Recording scope, option and value
            dnsmasq_dhcp_section.append_dhcp_option(
                    DNSMasq_DHCP_Option(
                        netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                        "6", default_dnsname_ip_addr))

    return dnsmasq_dhcp_section


# Get ntp from the configuration file for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_ntp(ctx, prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
    # Check if there is a specific prefix with ntp in the config file for its prefix
    if 'prefixes' in ctx and prefix_obj['prefix'] in ctx['prefixes'] and \
        'ntp' in ctx['prefixes'][prefix_obj['prefix']]:

        # Record the ntp server
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "42", ctx['prefixes'][prefix_obj['prefix']]['ntp']))

        return dnsmasq_dhcp_section

    # Write NTP server
    if 'dnsmasq_dhcp_default_ntp_server' in ctx and ctx['dnsmasq_dhcp_default_ntp_server'] is not None:
        dnsmasq_dhcp_section.append_dhcp_option(
                DNSMasq_DHCP_Option(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    "42", ctx['dnsmasq_dhcp_default_ntp_server']))

    return dnsmasq_dhcp_section


def netbox_process_prefix_into_dnsmasq_dhcp_section_range(ctx, prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
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

    return dnsmasq_dhcp_section


# Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
# Extract all IP addresses in the VRF
def netbox_process_prefix_into_dnsmasq_dhcp_section_hosts(ctx, prefix_obj, dnsmasq_dhcp_section) -> DNSMasq_DHCP_Section:
    dhcp_host_tuples = netboxers_queries.get_dhcp_host_dict_from_vrf(ctx, prefix_obj['vrf']['id'])

    for tup in dhcp_host_tuples:
        # When Device is set to Offline, skip it
        if tup['status'] != 'active':
            print(f"Device or virtual machine associated to the interface \"{tup['host_iface']}\" with MAC {tup['mac_address']} and IP address {tup['ip_addr']} is Offline, skipping.")
            continue

        # Record the DHCP host
        dnsmasq_dhcp_section.append_dhcp_host(
                DNSMasq_DHCP_Host(
                    netboxers_queries.get_vrf_vlan_name_from_prefix_obj(prefix_obj),
                    tup['mac_address'], tup['host_iface'],
                    tup['ip_addr'], ctx['dnsmasq_dhcp_default_lease_time_host']))

    return dnsmasq_dhcp_section


def netbox_process_prefix_into_dnsmasq_dhcp_section(ctx, prefix_obj) -> DNSMasq_DHCP_Section:
    dnsmasq_dhcp_section = DNSMasq_DHCP_Section()

    # Generate DNSMasq DHCP Section header information
    dnsmasq_dhcp_section = netbox_generate_dnsmasq_dhcp_section_header_info(prefix_obj, dnsmasq_dhcp_section)

    # Get default gateway gateway
    dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section_gateway(ctx, prefix_obj, dnsmasq_dhcp_section)

    # Get DNS server config
    dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section_dns(ctx, prefix_obj, dnsmasq_dhcp_section)

    # Add NTP server config
    dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section_ntp(ctx, prefix_obj, dnsmasq_dhcp_section)

    # Add IP Range of the DHCP pool
    dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section_range(ctx, prefix_obj, dnsmasq_dhcp_section)

    # Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
    # Extract all IP addresses in the VRF
    dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section_hosts(ctx, prefix_obj, dnsmasq_dhcp_section)

    # return results
    return dnsmasq_dhcp_section


def netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx, dnsmasq_dhcp_config) -> DNSMasq_DHCP_Config:
    # Get prefixes
    prefixes = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    if prefixes['count'] == 0:
        print("No prefixes found to complete")

    for prefix_obj in prefixes['results']:
        # Skip non-IPv4
        if prefix_obj['is_pool'] != True:
            continue

        # Only Active Prefixes
        if prefix_obj['status']['value'] != 'active':
            print("Prefix {} not active, skipping.".format(prefix_obj['prefix']))
            continue

        # Process the prefix. Output is a DNSMasq_DHCP_Section object
        dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section(ctx, prefix_obj)
        if dnsmasq_dhcp_section is None:
            raise f"Something happend processing the prefix {prefix_obj['prefix']}"

        # Record section to config
        dnsmasq_dhcp_config.append_to_dhcp_config_sections(dnsmasq_dhcp_section)
    
    return dnsmasq_dhcp_config
    

# This function will create a DNSMasq formatted DHCP config file from Netbox
## Create DNSMasq DHCP config file by:
## 1. Fetching defaults
## 2. Fetching VRFs, and VRF info.
## 3. Fetch associated default gateway and DNS config
## 4. Fetch (virtual) hosts and its data (IP and MAC)

def netbox_to_dnsmasq_dhcp_config(ctx):
    # Create DNSMasq DHCP config
    dnsmasq_dhcp_config = DNSMasq_DHCP_Config()

    # File header: set dhcp-leasefile
    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("dhcp-leasefile", ctx['dnsmasq_dhcp_lease_file']))

    # File header: set authoritive DHCP
    if ctx['dnsmasq_dhcp_authoritive']:
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-authoritative", None))

    # File header: set default domain
    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("domain", ctx['dnsmasq_dhcp_default_domain']))

    # File header: set PXE boot filename, servername and address
    if 'dnsmasq_dhcp_boot_filename' in ctx:
        dhcp_boot_elems = []
        dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_filename'])
        if 'dnsmasq_dhcp_boot_servername' in ctx:
            dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_servername'])
        if 'dnsmasq_dhcp_boot_address' in ctx:
            dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_address'])
        
        # Join the elements together with comma-delimeter
        dhcp_boot = ','.join(dhcp_boot_elems)

        # Finalize the configuration
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", dhcp_boot))

    # Get prefixes and process each
    dnsmasq_dhcp_config = netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx, dnsmasq_dhcp_config)

    # Truncate and open file cleanly
    netboxers_helpers.write_to_ddo_fh(ctx, None)

    ## Output DNSMasq Config to file
    netboxers_helpers.write_to_ddo_fh(ctx, str(dnsmasq_dhcp_config))


### Main
def main(ctx: {}):
    try:
        # Test if writing is possible of results
        netboxers_helpers.test_write_to_ddo_fh(ctx)
    except FileNotFoundError:
        print(f"Error: could not write to \'{ctx['dnsmasq_dhcp_output_file']}\'", file=sys.stderr)
        return

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