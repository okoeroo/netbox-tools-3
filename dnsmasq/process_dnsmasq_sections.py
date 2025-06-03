#!/usr/bin/env python3

import re
from ipaddress import ip_interface, ip_network
from netboxers.models.dnsmasq_dhcp import   DNSMasq_DHCP_Section, \
                                            DNSMasq_DHCP_Option, \
                                            DNSMasq_DHCP_Range, \
                                            DNSMasq_DHCP_Host, \
                                            DNSMasq_DHCP_Prefix
from netboxers.netboxers_queries import get_net_default_gateway_from_prefix, \
                                        get_dns_from_net_default_gateway_from_prefix, \
                                        get_range_from_prefix, \
                                        get_hosts_from_prefix

# All non-alfanum, replace with underscore and lowercase it
def sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '_', s).lower()


# Get default gateway for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_gateway(ctx: dict, 
                                                            prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Option | None:

    gateway = get_net_default_gateway_from_prefix(ctx, prefix_obj.get_prefix())
    if gateway is None:
        print(f"Warning: No \'{ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag']}\' configured for prefix {prefix_obj.get_prefix()}")
        return None

    # Parse to check if the input is OK
    ip = ip_interface(gateway)

    # Record the default gateway
    return DNSMasq_DHCP_Option(prefix_obj, "3", str(ip.ip))
    

# Get DNS server configuration for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_dns(ctx: dict,
                                                        prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Option | None:
    # Override from config or args, or fetch the config from netbox
    if default_dnsname_ip_addr := ctx.get('dnsmasq_dhcp_override_dns_server'):
        # Record the DNS server
        return DNSMasq_DHCP_Option(prefix_obj, "6", default_dnsname_ip_addr)

    dns = get_dns_from_net_default_gateway_from_prefix(ctx, prefix_obj.get_prefix())
    if not dns:
        print(f"Warning: No dns name set with the ip address with the tag \'{ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag']}\' configured for prefix {prefix_obj.get_prefix()}")
        return None

    # Parse to check if the input is OK
    ip = ip_interface(dns)

    return DNSMasq_DHCP_Option(prefix_obj, "6", str(ip.ip))


# Get ntp from the configuration file for the prefix
def netbox_process_prefix_into_dnsmasq_dhcp_section_ntp(ctx: dict,
                                                        prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Option | None:
    # Override from config or args, or fetch the config from netbox
    if default_ntp_ip_addr := ctx.get('dnsmasq_dhcp_default_ntp_server'):
        # Record the DNS server
        return DNSMasq_DHCP_Option(prefix_obj, "42", default_ntp_ip_addr)

    return None


# Get Domain search from the configuration file, which is a generich setting at the moment.
def netbox_process_prefix_into_dnsmasq_dhcp_section_domain_search(ctx: dict,
                                                                  prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Option| None:

    # Check if there is a specific domain search in the config file, which is a generic setting
    if domain_search := ctx.get('dnsmasq_dhcp_domain_search'):
        # Record the domain search domain
        return DNSMasq_DHCP_Option(prefix_obj, "119", domain_search)

    return None


def netbox_process_prefix_into_dnsmasq_dhcp_section_range(ctx: dict,
                                                          prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Range | None:
    netmask = ip_network(prefix_obj.get_prefix()).netmask
                                                          
    if tup := get_range_from_prefix(ctx, prefix_obj.get_prefix()):
        begin_addr, end_addr = tup
        return DNSMasq_DHCP_Range(prefix_obj, begin_addr, end_addr, netmask,
                                  ctx['dnsmasq_dhcp_default_lease_time_range'])

    return None


# Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
# Extract all IP addresses in the VRF
def netbox_process_prefix_into_dnsmasq_dhcp_section_hosts(ctx: dict, 
                                                          prefix_obj: DNSMasq_DHCP_Prefix) -> list[DNSMasq_DHCP_Host] | None:
    host_tuples = get_hosts_from_prefix(ctx, prefix_obj.get_prefix())
    if not host_tuples:
        return None

    dhcp_hosts: list[DNSMasq_DHCP_Host] = []
    for h in host_tuples:
        (mac_addr, dev_name, if_name, ip) = h

        host_iface = sanitize(f"{dev_name}_{if_name}")
        dhcp_hosts.append(DNSMasq_DHCP_Host(prefix_obj, 
                                            mac_addr,
                                            host_iface,
                                            ip,
                                            ctx['dnsmasq_dhcp_default_lease_time_host']))
        
    return dhcp_hosts


# Creation of a DHCP section.
def netbox_process_prefix_into_dnsmasq_dhcp_section(ctx: dict,
                                                    prefix_obj: DNSMasq_DHCP_Prefix) -> DNSMasq_DHCP_Section | None:
    """Use a DNSMasq_DHCP_Prefix as starting point to generate a DNSMasq_DHCP_Section

    Args:
        ctx (dict): Context 
        prefix_obj (_type_): Prefix object.

    Returns:
        DNSMasq_DHCP_Section | None: fully configured DHCP Section
    """

    # Create Section from Prefix input
    dnsmasq_dhcp_section = DNSMasq_DHCP_Section(prefix_obj)

    # Get default gateway gateway
    if dhcp_option := netbox_process_prefix_into_dnsmasq_dhcp_section_gateway(ctx, prefix_obj):
        dnsmasq_dhcp_section.append_dhcp_option(dhcp_option)

    # Get DNS server config
    if dhcp_option := netbox_process_prefix_into_dnsmasq_dhcp_section_dns(ctx, prefix_obj):
        dnsmasq_dhcp_section.append_dhcp_option(dhcp_option)

    # Add NTP server config
    if dhcp_option := netbox_process_prefix_into_dnsmasq_dhcp_section_ntp(ctx, prefix_obj):
        dnsmasq_dhcp_section.append_dhcp_option(dhcp_option)

    # Add Domain search config
    if dhcp_option := netbox_process_prefix_into_dnsmasq_dhcp_section_domain_search(ctx, prefix_obj):
        dnsmasq_dhcp_section.append_dhcp_option(dhcp_option)

    # Add IP Range of the DHCP pool
    if dhcp_range := netbox_process_prefix_into_dnsmasq_dhcp_section_range(ctx, prefix_obj):
        dnsmasq_dhcp_section.append_dhcp_range(dhcp_range)

    # Query all IP addresses in the VRF. From each, fetch the associated interface and its MAC
    # Extract all IP addresses in the VRF
    if dhcp_hosts := netbox_process_prefix_into_dnsmasq_dhcp_section_hosts(ctx, prefix_obj):
        for dh in dhcp_hosts:
            dnsmasq_dhcp_section.append_dhcp_host(dh)

    # return results
    return dnsmasq_dhcp_section
