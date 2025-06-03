#!/usr/bin/env python3

from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address, ip_interface

from netboxers import netboxers_helpers
from typing import Any


def netbox_query_obj(ctx: dict,
                     query: str,
                     **kwargs: Any) -> dict | None:
    # Setup
    parameters = dict(kwargs)

    # Query
    result = netboxers_helpers.query_netbox(ctx, query, parameters)
    
    # Result
    return result
                     

# Generic query
def netbox_query_list(ctx: dict,
                      subquery: str,
                      **kwargs: Any) -> dict | list | None:
    # Setup
    parameters = dict(kwargs)

    # Query
    results = netboxers_helpers.query_netbox(ctx, subquery, parameters)
    
    # Result
    return results['results'] if results['count'] > 0 else None


# Default gateway based on a selector.
def get_net_default_gateway_from_prefix(ctx: dict, 
                                        prefix: IPv4Network | IPv6Network) -> str | None:
    """Get the ip-address found in the prefix with the tag set in the context
    with the value for
    'dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'

    Args:
        ctx (dict): Context
        prefix (IPv4Network | IPv6Network): Prefix in the form 192.168.1.0/24

    Returns:
        str | None: ip address or None
    """
    results = netbox_query_list(ctx, 
                           "ipam/ip-addresses/", 
                           parent = str(prefix), 
                           tag = ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'])

    return results[0]['address'] if results else None


def get_dns_from_net_default_gateway_from_prefix(ctx: dict,
                                                 prefix: IPv4Network | IPv6Network) -> str | None:
    """Get the dns-name value set to the ip-address found in the prefix with the
    tag set in the context with the value for
    'dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'

    Args:
        ctx (dict): Context
        prefix (IPv4Network | IPv6Network): Prefix in the form 192.168.1.0/24

    Returns:
        str | None: ip address or None
    """
    results = netbox_query_list(ctx, 
                           "ipam/ip-addresses/", 
                           parent = str(prefix), 
                           tag = ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'])

    return results[0]['dns_name'] if results else None


def get_range_from_prefix(ctx: dict,
                          prefix: IPv4Network | IPv6Network) -> tuple[IPv4Address | IPv6Address, IPv4Address | IPv6Address] | None:
    if results := netbox_query_list(ctx,
                               "ipam/ip-ranges/",
                               status = 'active',
                               tag = ctx['dnsmasq_dhcp_selected_range_in_prefix_by_tag']):
        # filter range to match by the prefix
        for range in results:
            begin_addr = ip_interface(range['start_address'])
            end_addr   = ip_interface(range['end_address'])
            
            if begin_addr in prefix and end_addr in prefix:
                return begin_addr.ip, end_addr.ip

    # No range found that fits the prefix.
    return None


# dhcp-host=vrf_204_IoT_net_vlan_204,24:62:AB:48:F0:07,tasmota_switch_4_wlan0,192.168.204.104,90m
def get_hosts_from_prefix(ctx: dict,
                          prefix: IPv4Network | IPv6Network) -> list[tuple] | None:

    hosts_list: list[tuple] = []
                          
    # From IP addr go to assigned_object: interface['url'] for interface object. 
    ip_addrs_in_prefix = netbox_query_list(ctx, 
                                           "ipam/ip-addresses/", 
                                           parent = str(prefix),
                                           status = 'active')
    if not ip_addrs_in_prefix:
        return None
        
    if ip_addrs_in_prefix := netbox_query_list(ctx, 
                                          "ipam/ip-addresses/", 
                                          parent = str(prefix),
                                          status = 'active'):

        for ip_addr in ip_addrs_in_prefix:
            if assigned_object := ip_addr.get('assigned_object'):
                if assigned_object_url := assigned_object.get('url'):
                    stripped_url = assigned_object_url.split("/api/", 1)[1]

                    interface_obj = netbox_query_obj(ctx, stripped_url)
                    if interface_obj:
                        mac_addr = interface_obj.get('mac_address')
                        dev_name = interface_obj['device']['name'] if interface_obj.get('device') else interface_obj['virtual_machine']['name']
                        if_name  = interface_obj['name']
                        ip       = ip_interface(ip_addr['address']).ip

                        tup = (mac_addr, dev_name, if_name, ip)
                        hosts_list.append(tup)

        return hosts_list


def get_status_of_devvm_from_ipaddresses_obj(ctx: dict, ip_addr_obj: dict):
    obj = netboxers_helpers.query_netbox(ctx, ip_addr_obj['assigned_object']['url'])

    if 'device' in obj:
        dev = netboxers_helpers.query_netbox(ctx, obj['device']['url'])
        return dev['status']['value']
    elif 'virtual_machine' in obj:
        vm = netboxers_helpers.query_netbox(ctx, obj['virtual_machine']['url'])
        return vm['status']['value']
    else:
        raise ValueError("Assigned object is not a device nor a virtual_machine.")



## Based on the mac address fetch a device.
## The device can be a virtual machine or device
def fetch_devices_from_mac_address(ctx: dict, mac_address: str) -> dict | None:
    parameters = {}
    parameters['mac_address'] = mac_address

    # Device or VM?
    devices = netboxers_helpers.query_netbox(ctx, "dcim/devices/", parameters)
    if devices['count'] == 0:
        devices = netboxers_helpers.query_netbox(ctx, "virtualization/virtual-machines/", parameters)
        if devices['count'] == 0:
            # Not in Database...
            return None

    return devices
