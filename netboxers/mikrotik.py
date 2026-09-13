#!/usr/bin/env python3

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


def mikrotik_pool_netbox_ranges_sync(ctx: dict) -> bool:
    j_netbox_ip_ranges = netbox_query_list(ctx,
                                           "ipam/ip-ranges/",
                                           tag = ctx['dhcpv4_tag_for_dhcp_range'],
                                           status = "active",
                                           family = 4)

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


"""
/ip dhcp-server
add address-pool=pool-ether2 interface=ether2 name=dhcp-ether2

/ip dhcp-server network
add address=192.168.207.0/24 dns-server=1.2.3.4 gateway=192.168.207.1 netmask=24 ntp-server=192.168.1.1
"""

