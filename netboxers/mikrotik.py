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
def mikrotik_key_val_exists(ctx: dict, locator: str, key: str, val: str) -> bool:
    mikro_list = mikrotik_get(ctx, locator)
    for elem in mikro_list:
        if elem[key] == val:
            return elem['.id']
    return None


# Returns None, or the (first) id it matches
def mikrotik_name_exists(ctx: dict, locator: str, name: str) -> bool:
    return mikrotik_key_val_exists(ctx, locator, "name", name)


# Returns None, or the (first) id it matches
def mikrotik_pool_exists(ctx: dict, name: str) -> bool:
    return mikrotik_name_exists(ctx, "/ip/pool", name)



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

        pool_id = mikrotik_name_exists(ctx, "/ip/pool", safe_name(f"pool-{ip_range['vrf']['name']}"))
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
                           comment = ip_range['vrf']['description'] + "_1",
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

    target_ip = ipaddress.ip_interface(ipaddr).ip
    target_router = netbox_get_target_router_device(ctx)

    if not target_router or not 'interfaces' in target_router or not target_router['interfaces']:
        print("Error: targer router not properly configured. Missing interface data")
        return None

    for iface in target_router["interfaces"]:
        for iface_ip in iface["ipv4"] + iface["ipv6"]:
            if target_ip == ipaddress.ip_interface(iface_ip).ip:
                return iface

    return None



def netbox_fetch_assigned_object(ctx: dict, obj: dict) -> dict | None:
    interface = None
    if 'assigned_object_type' not in obj or not obj['assigned_object_type']:
        return None

    if obj['assigned_object_type'] == 'dcim.interface':
        interface = netbox_query_list(ctx, "dcim/interfaces",
                                      id = obj['assigned_object']['id'])
    elif obj['assigned_object_type'] == 'virtualization.vminterface':
        interface = netbox_query_list(ctx, "virtualization/interfaces",
                                      id = obj['assigned_object']['id'])
    return interface


def netbox_fetch_assigned_object_by_ipaddr(ctx: dict,
                                           vrf_id: int,
                                           ipaddr: ipaddress.IPv4Interface | ipaddress.IPv6Interface) -> dict | None:
    if not ipaddr:
        return None

    ipaddresses = netbox_query_list(ctx, "ipam/ip-addresses",
                                    vrf_id = vrf_id,
                                    address = ipaddr.with_prefixlen)
    if ipaddresses:
        for ipaddr in ipaddresses:
            return netbox_fetch_assigned_object(ctx, ipaddr)

    return None



def netbox_dhcp_configs(ctx: dict, netbox_vrfs_merged: list) -> dict:
    dhcp_configs = []

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
                        dhcp_config['start_address'] = ipaddress.ip_interface(ra['start_address'])
                        dhcp_config['end_address']   = ipaddress.ip_interface(ra['end_address'])

                dhcp_config['gateway'] = netbox_get_first_match_by_ip(ctx, "net_default_gateway", vrf['id'], 4)
                if dhcp_config['gateway']:
                    dhcp_config['subnet'] = ipaddress.ip_interface(dhcp_config['gateway']).network

                gateway_interface = netbox_fetch_assigned_object_by_ipaddr(ctx, vrf['id'], dhcp_config['gateway'])
                if gateway_interface:
                    dhcp_config['gateway_interface'] = gateway_interface

                dhcp_config['dns'] = netbox_get_first_match_by_ip(ctx, "net_default_dns", vrf['id'], 4)

                dhcp_config['ntp'] = netbox_get_first_match_by_ip(ctx, "net_default_ntp", vrf['id'], 4)

#                if 'ipv4addrs' in vrf:
#                    for ipv4 in vrf['ipv4addrs']:
#                        print(ipv4['address'])
#                        ipv4['fetched_interface'] = netbox_fetch_assigned_object(ctx, ipv4)
#
#                if 'ipv6addrs' in vrf:
#                    for ipv6 in vrf['ipv6addrs']:
#                        print(ipv4['address'])
#                        ipv6['fetched_interface'] = netbox_fetch_assigned_object(ctx, ipv6)

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

    return dhcp_configs


def mikrotik_configure(ctx: dict, dhcp_configs: dict) -> None:
    # mikrotik configs
    for dhcp_config in dhcp_configs:
        if dhcp_config['gateway_interface']:
            if 'untagged_vlan' in dhcp_config['gateway_interface'][0] and 'display' in dhcp_config['gateway_interface'][0]['untagged_vlan']:
                comment = dhcp_config['gateway_interface'][0]['untagged_vlan']['display']
                dhcp_config['comment'] = comment
            else:
                comment = dhcp_config['gateway_interface'][0]['display']
                dhcp_config['comment'] = comment

        # pool
        mikrotik_add_update_pool(ctx, dhcp_config)

        # dhcp server
        mikrotik_add_update_dhcp_server(ctx, dhcp_config)

        # dhcp server network
        mikrotik_add_update_dhcp_server_network(ctx, dhcp_config)


def mikrotik_add_update_pool(ctx: dict, dhcp_config: dict) -> bool:
        if dhcp_config['start_address'] and dhcp_config['end_address']:
            dhcp_pool = []
            dhcp_pool.append(f"/ip pool add")
            dhcp_pool.append(f"name=pool-{dhcp_config['targer_router_interface']['name']}")
            dhcp_pool.append(f"ranges={dhcp_config['start_address'].ip}-{dhcp_config['end_address'].ip}")
            dhcp_pool.append(f"comment=\"{dhcp_config['comment']}\"")
            print(f"{" ".join(dhcp_pool)}")


        begin_ip = dhcp_config['start_address'].ip
        end_ip   = dhcp_config['end_address'].ip

        params = {
            "comment": dhcp_config["comment"],
            "name": f"pool-{dhcp_config['targer_router_interface']['name']}",
            "ranges": f"{begin_ip}-{end_ip}",
        }

        pool_id = mikrotik_name_exists(ctx, "/ip/pool", f"pool-{dhcp_config['targer_router_interface']['name']}")
        if not pool_id:
            mikrotik_put(ctx, "/ip/pool", **params)
        else:
            mikrotik_patch(ctx, f"/ip/pool/{pool_id}", **params)


def mikrotik_add_update_dhcp_server(ctx: dict, dhcp_config: dict) -> bool:
        dhcp_server = []
        dhcp_server.append(f"/ip dhcp-server add")
        dhcp_server.append(f"name=dhcp-{dhcp_config['targer_router_interface']['name']}")
        dhcp_server.append(f"address-pool=pool-{dhcp_config['targer_router_interface']['name']}")
        dhcp_server.append(f"interface={dhcp_config['targer_router_interface']['name']}")
        dhcp_server.append(f"comment=\"{dhcp_config['comment']}\"")
        print(f"{" ".join(dhcp_server)}")

        params = {
            "name": f"dhcp-{dhcp_config['targer_router_interface']['name']}",
            "address-pool": f"pool-{dhcp_config['targer_router_interface']['name']}",
            "interface": dhcp_config["targer_router_interface"]["name"],
            "comment": dhcp_config["comment"],
        }
        dhcp_server_id = mikrotik_name_exists(ctx, "/ip/dhcp-server", f"dhcp-{dhcp_config['targer_router_interface']['name']}")
        if not dhcp_server_id:
            mikrotik_put(ctx, "/ip/dhcp-server", **params)
        else:
            mikrotik_patch(ctx, f"/ip/dhcp-server/{dhcp_server_id}", **params)


def mikrotik_add_update_dhcp_server_network(ctx: dict, dhcp_config: dict) -> bool:
        dhcp_server_network = []
        dhcp_server_network.append(f"/ip dhcp-server network add")
        dhcp_server_network.append(f"address={dhcp_config['subnet']}")
        dhcp_server_network.append(f"comment=\"{dhcp_config['comment']}\"")
        if 'gateway' in dhcp_config and dhcp_config['gateway']:
            dhcp_server_network.append(f"gateway={dhcp_config['gateway'].ip}")
        if 'dns' in dhcp_config and dhcp_config['dns']:
            dhcp_server_network.append(f"dns-server={dhcp_config['dns'].ip}")
        if 'ntp' in dhcp_config and dhcp_config['ntp']:
            dhcp_server_network.append(f"ntp-server={dhcp_config['ntp'].ip}")
        print(f"{" ".join(dhcp_server_network)}")

        params = {
            "address": str(dhcp_config["subnet"]),
            "comment": dhcp_config["comment"],
        }

        if 'gateway' in dhcp_config and dhcp_config['gateway']:
            params['gateway'] = str(dhcp_config["gateway"].ip)

        if 'dns' in dhcp_config and dhcp_config['dns']:
            params['dns-server'] = str(dhcp_config["dns"].ip)

        if 'ntp' in dhcp_config and dhcp_config['ntp']:
            params['ntp-server'] = str(dhcp_config["ntp"].ip)


        # check if the addresss (subnet here) exists in the dhcp-server network
        dhcp_server_network_id = mikrotik_key_val_exists(ctx, "/ip/dhcp-server/network", "address", f"{dhcp_config['subnet']}")
        if not dhcp_server_network_id:
            mikrotik_put(ctx, "/ip/dhcp-server/network", **params)
        else:
            mikrotik_patch(ctx, f"/ip/dhcp-server/network/{dhcp_server_network_id}", **params)


