#!/usr/bin/env python3

from printer import printer

import sys
import requests
import ipaddress
from typing import Any

from netboxers.netboxers_helpers import write_data_to_file
from netboxers.netboxers_queries import fetch_active_prefixes, netbox_query_list
from netboxers.models.netbox import Netbox_Prefix



def safe_name(name: str) -> str:
    return name.replace("/", "__").replace(" ", "_").replace("*", "_")


def mikrotik_get(ctx: dict,
                 subquery: str,
                 **kwargs: dict[str, Any] | None) -> dict[str, Any] | list[dict[str, Any]]:

    parameters = dict(kwargs)

    endpoint = ctx.get('mikrotik_endpoint')
    username = ctx.get('mikrotik_username')
    password = ctx.get('mikrotik_password')

    url = f"{endpoint if endpoint.startswith(('http://', 'https://')) else 'http://' + endpoint}"
    url = f"{url.rstrip('/')}/rest/{subquery.lstrip('/')}"

    response = requests.get(
        url,
        auth=(username, password),
        params=parameters,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def mikrotik_get_ipaddresses(ctx: dict) -> dict[str, Any] | list[dict[str, Any]]:
    subquery = "/ip/address"
    params={"interface": "ether2"}

    return mikrotik_query(ctx, subquery, params)


def mikrotik_put(ctx: dict,
                 subquery: str,
                 **kwargs: dict[str, Any] | None) -> dict[str, Any] | list[dict[str, Any]]:

    parameters = dict(kwargs)

    endpoint = ctx.get('mikrotik_endpoint')
    username = ctx.get('mikrotik_username')
    password = ctx.get('mikrotik_password')

    url = f"{endpoint if endpoint.startswith(('http://', 'https://')) else 'http://' + endpoint}"
    url = f"{url.rstrip('/')}/rest/{subquery.lstrip('/')}"

    response = requests.put(
        url,
        auth=(username, password),
        json=parameters,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def mikrotik_patch(ctx: dict,
                   subquery: str,
                   **kwargs: dict[str, Any] | None) -> dict[str, Any] | list[dict[str, Any]]:

    parameters = dict(kwargs)

    endpoint = ctx.get('mikrotik_endpoint')
    username = ctx.get('mikrotik_username')
    password = ctx.get('mikrotik_password')

    url = f"{endpoint if endpoint.startswith(('http://', 'https://')) else 'http://' + endpoint}"
    url = f"{url.rstrip('/')}/rest/{subquery.lstrip('/')}"

    response = requests.put(
        url,
        auth=(username, password),
        json=parameters,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# Returns None, or the (first) id it matches
def mikrotik_pool_exists(ctx: dict, name: str) -> bool:
    # Get pools
    j_mikro_pools = mikrotik_get(ctx, "/ip/pool")
    for m_pool in j_mikro_pools:
        if m_pool['name'] == name:
            return m_pool['.id']

    return None



def netbox_get_target_router_device(ctx: dict) -> dict[str, Any]:
    target_ip = ipaddress.ip_interface(
        ctx["mikrotik_target_router"]
    ).ip

    ip_matches = netbox_query_list(
        ctx,
        "ipam/ip-addresses/",
        address=str(target_ip),
    )

    owners = {}

    for item in ip_matches:
        assigned = item.get("assigned_object")
        kind = item.get("assigned_object_type")

        if not assigned:
            continue

        if kind == "dcim.interface":
            owner = assigned["device"]
        elif kind == "virtualization.vminterface":
            owner = assigned["virtual_machine"]
        else:
            continue

        owners[(kind, owner["id"])] = owner

    if not owners:
        raise ValueError(
            f"Geen device of VM gevonden voor {target_ip}"
        )

    if len(owners) > 1:
        raise ValueError(
            f"Meerdere devices/VM's gevonden voor {target_ip}; "
            "filter de IP-query bijvoorbeeld met vrf_id."
        )

    (kind, owner_id), owner = next(iter(owners.items()))

    if kind == "dcim.interface":
        owner_type = "device"
        interface_endpoint = "dcim/interfaces/"
        interface_filter = {"device_id": owner_id}
        ip_filter_name = "interface_id"
    else:
        owner_type = "virtual_machine"
        interface_endpoint = "virtualization/interfaces/"
        interface_filter = {"virtual_machine_id": owner_id}
        ip_filter_name = "vminterface_id"

    target_router = {
        "id": owner_id,
        "name": owner["name"],
        "type": owner_type,
        "target_ip": target_ip,
        "interfaces": [],
    }

    interfaces = netbox_query_list(
        ctx,
        interface_endpoint,
        **interface_filter,
    )

    for iface in interfaces:
        primary_mac = iface.get("primary_mac_address") or {}

        interface_data = {
            "id": iface["id"],
            "name": iface["name"],
            "enabled": iface.get("enabled"),
            "mac_address": (
                primary_mac.get("mac_address")
                or iface.get("mac_address")
                or None
            ),
            "ipv4": [],
            "ipv6": [],
        }

        ip_records = netbox_query_list(
            ctx,
            "ipam/ip-addresses/",
            **{ip_filter_name: iface["id"]},
        )

        for record in ip_records:
            address = ipaddress.ip_interface(record["address"])
            key = "ipv4" if address.version == 4 else "ipv6"
            interface_data[key].append(address)

        target_router["interfaces"].append(interface_data)

    return target_router


def netbox_get_ip_addresses_with_tag(ctx: dict, tag: str) -> list[dict[str, Any]]:
    return netbox_query_list(
        ctx,
        "ipam/ip-addresses/",
        tag=tag
    )


def netbox_vrf_merge_elements(ctx: dict) -> list[dict[str, Any]]:
    vrfs = netbox_query_list(ctx, "ipam/vrfs/")
    prefixes = netbox_query_list(ctx, "ipam/prefixes/", status = 'active')
    ranges = j_netbox_ip_ranges = netbox_get_ip_ranges_ipv4(ctx)
    ipv4addrs = netbox_query_list(ctx, "ipam/ip-addresses/", status = 'active', family = 4)
    ipv6addrs = netbox_query_list(ctx, "ipam/ip-addresses/", status = 'active', family = 6)


    for vrf in vrfs:
        for prefix in prefixes:
            if vrf['id'] == prefix['vrf']['id']:
                if 'prefixes' not in vrf:
                    vrf['prefixes'] = []

                vrf['prefixes'].append(prefix)

        for ra in ranges:
            if vrf['id'] == ra['vrf']['id']:
                if 'ranges' not in vrf:
                    vrf['ranges'] = []

                vrf['ranges'].append(ra)

        for ip in ipv4addrs:
            if 'vrf' in ip and ip['vrf'] and 'id' in ip['vrf'] and vrf['id'] == ip['vrf']['id']:
                if 'ipv4addrs' not in vrf:
                    vrf['ipv4addrs'] = []

                vrf['ipv4addrs'].append(ip)

        for ip in ipv6addrs:
            if 'vrf' in ip and ip['vrf'] and 'id' in ip['vrf'] and vrf['id'] == ip['vrf']['id']:
                if 'ipv6addrs' not in vrf:
                    vrf['ipv6addrs'] = []

                vrf['ipv6addrs'].append(ip)

    return vrfs


def netbox_get_ip_ranges_ipv4(ctx: dict) -> dict[str, Any]:
    j_netbox_ip_ranges = netbox_query_list(ctx,
                                           "ipam/ip-ranges/",
                                           tag = ctx['dhcpv4_tag_for_dhcp_range'],
                                           status = "active",
                                           family = 4)
    return j_netbox_ip_ranges



def mikrotik_pool_netbox_ranges_sync(ctx: dict) -> bool:
    j_netbox_ip_ranges = netbox_get_ip_ranges_ipv4(ctx)

    for ip_range in j_netbox_ip_ranges:
        begin_ip = ipaddress.ip_interface(ip_range['start_address']).ip
        end_ip = ipaddress.ip_interface(ip_range['end_address']).ip

        pool_id = mikrotik_pool_exists(ctx, safe_name(f"pool-{ip_range['vrf']['name']}"))
        if not pool_id:
            mikrotik_put(ctx,
                         "/ip/pool",
                         comment = ip_range['vrf']['description'],
                         name = safe_name(f"pool-{ip_range['vrf']['name']}"),
                         ranges = f"{begin_ip}-{end_ip}"
                         )
        else:
            mikrotik_patch(ctx,
                           f"/ip/pool/{pool_id}",
                           comment = ip_range['vrf']['description'],
                           name = safe_name(f"pool-{ip_range['vrf']['name']}"),
                           ranges = f"{begin_ip}-{end_ip}"
                           )


def netbox_get_first_match_by_ip(ctx: dict,
                                 tag: str,
                                 vrf_id: int,
                                 family: int) -> ipaddress.IPv4Interface | ipaddress.IPv6Interface | None:
    ipaddrs = netbox_query_list(ctx, "ipam/ip-addresses/",
                                    tag = tag,
                                    vrf_id = vrf_id,
                                    family = family)
    if len(ipaddrs):
        for ip in ipaddrs:
            return ipaddress.ip_interface(ip['address'])
    return None



def target_router_get_interface_by_ipaddress(ctx: dict,
                                             ipaddr: ipaddress.IPv4Interface | ipaddress.IPv6Interface) -> dict | None:
    if not ipaddr:
        return None

    target_router = netbox_get_target_router_device(ctx)

    if not target_router or not 'interfaces' in target_router or not target_router['interfaces']:
        print("Error: targer router not properly configured. Missing interface data")
        return None

    for iface in target_router['interfaces']:
        for iface_ip in iface['ipv4']:
            if ipaddress.ip_interface(ipaddr).ip == ipaddress.ip_interface(iface_ip).ip:
                return iface
        for iface_ip in iface['ipv6']:
            if ipaddress.ip_interface(ipaddr).ip == ipaddress.ip_interface(iface_ip).ip:
                return iface

    return None


def netbox_dhcp_configs(ctx: dict, netbox_vrfs_merged: list):
    dhcp_configs = []

    print("************")

    # Per VRF, form and merge into configs
    for vrf in netbox_vrfs_merged:
        dhcp_config = {}

        print("&&&&&&&&&&&&&&&&&&&&&")
        if 'prefixes' in vrf:
            for prefix in vrf['prefixes']:
                print(prefix['prefix'])

                # Select the range (only support one per prefix)
                if 'ranges' in vrf:
                    for ra in vrf['ranges']:
                        dhcp_config['start_address'] = ra['start_address']
                        dhcp_config['end_address']   = ra['end_address']

                dhcp_config['gateway'] = netbox_get_first_match_by_ip(ctx,
                                                                      "net_default_gateway",
                                                                      vrf['id'],
                                                                      4)
                dhcp_config['dns'] = netbox_get_first_match_by_ip(ctx,
                                                                  "net_default_dns",
                                                                  vrf['id'],
                                                                  4)
                dhcp_config['ntp'] = netbox_get_first_match_by_ip(ctx,
                                                                  "net_default_ntp",
                                                                  vrf['id'],
                                                                  4)
#                if 'ipv4addrs' in vrf:
#                    for ipv4 in vrf['ipv4addrs']:
#                        print(ipv4['address'])

#                if 'ipv6addrs' in vrf:
#                    for ipv6 in vrf['ipv6addrs']:
#                        print(ipv4['address'])

                # Match on target router interface details, by looking up the intended gateway.
                t_router_iface = target_router_get_interface_by_ipaddress(ctx, dhcp_config['gateway'])
                dhcp_config['targer_router_interface'] = t_router_iface


        if not dhcp_config or ('gateway' in dhcp_config and not dhcp_config['gateway']):
            print("Notice: Ignoring this entry: it has no gateway.")
            continue

        if not dhcp_config['targer_router_interface']:
            print("Warning: Ignoring this entry: gateway configuration not matched on target router")
            continue

        # Add config
        dhcp_configs.append(dhcp_config)

    print("=>")
    printer(dhcp_configs)



"""
/ip pool
add name=pool-ether2 ranges=192.168.207.155-192.168.207.254

/ip dhcp-server
add address-pool=pool-ether2 interface=ether2 name=dhcp-ether2

/ip dhcp-server network
add address=192.168.207.0/24 dns-server=1.2.3.4 gateway=192.168.207.1 netmask=24 ntp-server=192.168.1.1
"""


