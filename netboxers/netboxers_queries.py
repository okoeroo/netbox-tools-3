#!/usr/bin/env python3

import requests
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address, ip_interface

from netboxers import netboxers_helpers
from typing import Any


def strip_query(ctx: dict, query: str):
    # Pattern is base_url/api/query, all double bits should be stripped 

    if query.startswith(ctx['generic_netbox_base_url'] + '/api/'):
        return query[len(ctx['generic_netbox_base_url'] + '/api/'):]

    return query

def query_netbox_call(ctx: dict, query: str, req_parameters: dict | None = None):
    if not 'http_session_handle' in ctx:
        ctx['http_session_handle'] = requests.Session()

    session = ctx['http_session_handle']

    req_headers = {}
    req_headers['Authorization'] = " ".join(["Token", ctx['generic_authkey']])
    req_headers['Content-Type'] = "application/json"
    req_headers['Accept'] = "application/json; indent=4"

    query_stripped = strip_query(ctx, query)

    if ctx['generic_verbose']:
        print(query_stripped)

    get_req = session.get('{}/api/{}'.format(ctx['generic_netbox_base_url'], query_stripped),
                           timeout=10,
                           headers=req_headers,
                           params=req_parameters)
    get_req.raise_for_status()

    if ctx['generic_verbose']:
        print(get_req.text)

    # Results retrieved
    return get_req.json()


def query_netbox(ctx: dict, query: str, req_parameters: dict | None = None):

    # Results retrieved
    response = query_netbox_call(ctx, query, req_parameters)

    # Merge response in memory
    req_next = response # setups for loop
    while 'next' in req_next and req_next['next'] and len(req_next['next']) > 0:
        res_next = query_netbox_call(ctx, req_next['next'], req_parameters)

        if ctx['generic_verbose']:
            print(res_next)

        for i in res_next['results']:
            response['results'].append(i)

        req_next = res_next

    return response


def netbox_query_obj(ctx: dict,
                     query: str,
                     **kwargs: Any) -> dict | None:
    # Setup
    parameters = dict(kwargs)

    # Query
    result = query_netbox(ctx, query, parameters)
    
    # Result
    return result
                     

# Generic query
def netbox_query_list(ctx: dict,
                      subquery: str,
                      **kwargs: Any) -> dict | list | None:
    # Setup
    parameters = dict(kwargs)

    # Query
    results = query_netbox(ctx, subquery, parameters)
    
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

    requested = cache_netbox_query_list(ctx, "ipam/ip-addresses/")
    
    if unfiltered := cache_netbox_query_list(ctx, "ipam/ip-addresses/"):
        with_tag = [d for d in unfiltered if d['tag']['value'] == ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag']]

        print(with_tag)
    
    return None
    
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


def get_assigned_interface_from_ip_address(ctx: dict, ip_addr: dict) -> dict | None:
    assigned_id = ip_addr.get('assigned_object', {}).get('id')
    if assigned_id:
        return next((i for i in ctx['cache']['dcim/interfaces/'] if i['id'] == assigned_id), None)
    return None


# dhcp-host=vrf_204_IoT_net_vlan_204,24:62:AB:48:F0:07,tasmota_switch_4_wlan0,192.168.204.104,90m
def get_hosts_from_prefix(ctx: dict,
                          prefix: IPv4Network | IPv6Network) -> list[tuple[str | None, str, str, IPv4Address | IPv6Address, dict]] | None:

    hosts_list: list[tuple[str | None, str, str, IPv4Address | IPv6Address, dict]] = []
                          
    # From IP addr go to assigned_object: interface['url'] for interface object. 
    unfiltered_ip_addrs = cache_netbox_query_list(ctx, "ipam/ip-addresses/")
    if not unfiltered_ip_addrs:
        return None

    ip_addrs_in_prefix = [ip_addr for ip_addr in unfiltered_ip_addrs 
                                    if ip_addr['status']['value'] == 'active' and 
                                    ip_interface(ip_addr['address']).ip in prefix] 
    if not ip_addrs_in_prefix:
        return None
        
    
    for ip_addr in ip_addrs_in_prefix:
        interface_obj = get_assigned_interface_from_ip_address(ctx, ip_addr)
        if not interface_obj:
            continue

        mac_addr      = interface_obj.get('mac_address')
        dev_name      = interface_obj['device']['name'] if interface_obj.get('device') else interface_obj['virtual_machine']['name']
        if_name       = interface_obj['name']
        ip            = ip_interface(ip_addr['address']).ip
        interface_obj = interface_obj

        tup: tuple[str | None, 
                    str, 
                    str, 
                    IPv4Address | IPv6Address, 
                    dict] = (mac_addr, dev_name, if_name, ip, interface_obj)

        hosts_list.append(tup)

    return hosts_list


def get_status_of_devvm_from_ipaddresses_obj(ctx: dict, ip_addr_obj: dict):
    obj = query_netbox(ctx, ip_addr_obj['assigned_object']['url'])

    if 'device' in obj:
        dev = query_netbox(ctx, obj['device']['url'])
        return dev['status']['value']
    elif 'virtual_machine' in obj:
        vm = query_netbox(ctx, obj['virtual_machine']['url'])
        return vm['status']['value']
    else:
        raise ValueError("Assigned object is not a device nor a virtual_machine.")


def get_status_of_devvm_from_ipaddresses_obj_from_dev_vm_list(ctx: dict, 
                                                              ip_addr_obj: dict, 
                                                              devices: list[dict] | None, 
                                                              vms: list[dict] | None) -> str | None:
    match = None

    if not ip_addr_obj.get('assigned_object'):
        # No assignment of IP to a device.
        return None

    if devices and \
        (assigned_object := ip_addr_obj.get('assigned_object')) and \
        (device := assigned_object.get('device')):

        device_id = ip_addr_obj['assigned_object']['device']['id']
        match = next((item for item in devices if item["id"] == device_id), None)

    elif vms and \
        (assigned_object := ip_addr_obj.get('assigned_object')) and \
        (vm := assigned_object.get('virtual_machine')):

        vm_id = ip_addr_obj['assigned_object']['virtual_machine']['id']
        match = next((item for item in vms if item["id"] == vm_id), None)

    if not match:
        return None

    return match['status']['value']


## Based on the mac address fetch a device.
## The device can be a virtual machine or device
def fetch_devices_from_mac_address(ctx: dict, mac_address: str) -> dict | None:
    parameters = {}
    parameters['mac_address'] = mac_address

    # Device or VM?
    devices = query_netbox(ctx, "dcim/devices/", parameters)
    if devices['count'] == 0:
        devices = query_netbox(ctx, "virtualization/virtual-machines/", parameters)
        if devices['count'] == 0:
            # Not in Database...
            return None

    return devices


# Fetch data which is useful multiple times.
def prefill_cache(ctx: dict) -> dict:
    ctx['cache'] = {}

    print("Info: Loading NetBox data...")

    endpoints = [
        "dcim/devices/",
        "virtualization/virtual-machines/",
        "dcim/interfaces/",
        "ipam/prefixes/",
        "ipam/ip-addresses/",
        "ipam/ip-ranges/",
    ]

    for endpoint in endpoints:
        print(f"Info: Loading: \'{endpoint}\'")
        ctx['cache'][endpoint] = netbox_query_list(ctx, endpoint)    

    print("Info: Done loading NetBox data.")
    return ctx


def cache_netbox_query_list(ctx: dict,
                            subquery: str) -> dict | list | None:
    
    if (cache := ctx.get('cache')) and (requested := cache.get(subquery)):
        return requested
    
    return netbox_query_list(ctx, subquery)