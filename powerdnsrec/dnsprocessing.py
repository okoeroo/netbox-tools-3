from pathlib import Path
import ipaddress
from ipaddress import IPv4Interface, IPv6Interface, ip_interface

from netboxers import netboxers_helpers
from netboxers.netboxers_helpers import make_iface_dot_host_name
from netboxers.netboxers_queries import netbox_query_obj, \
                                        get_status_of_devvm_from_ipaddresses_obj, \
                                        get_hosts_from_prefix
from netboxers.models.netbox import Netbox_Prefix
from netboxers.models.dns_zonefile import DNS_Zonefile, DNS_Resource_Record



def create_zone_defaults(ctx: dict) -> DNS_Zonefile:
    zo = DNS_Zonefile()

    # SOA
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

    # NS
    rr = DNS_Resource_Record(
            rr_type = 'NS',
            rr_name = '@',
            rr_data = 'ns.' + ctx['powerdns_rec_domain'])
    zo.add_rr(rr)
    return zo


def fetch_active_prefixes(ctx: dict) -> list[Netbox_Prefix]:
    # Get prefixes
    prefixes = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    if prefixes['count'] == 0:
        raise ValueError("No prefixes found in netbox to complete")

    # Select which prefixes to work on
    res = []
    for p in prefixes['results']:
        np = Netbox_Prefix(p)
        if np.is_active():
            res.append(np)
        else:
            print(f"Notice: skipping prefix \"{np.get_prefix()} due to configured filter constrains.")
    return res
    

def powerdns_recursor_zonefile(ctx) -> DNS_Zonefile:
    # Setup defaults
    zo = create_zone_defaults(ctx)

    ready_to_process_prefixes: list[Netbox_Prefix] = fetch_active_prefixes(ctx)

    # Work on these
    for prefix_obj in ready_to_process_prefixes:
        host_tuples = get_hosts_from_prefix(ctx, prefix_obj.get_prefix())
        if not host_tuples:
            continue

        for h in host_tuples:
            (_, dev_name, if_name, ip, interface_obj) = h

            iface_hostname = make_iface_dot_host_name(dev_name, if_name)

            # Add the A record for each interface
            rr = DNS_Resource_Record(
                    rr_type = 'A',
                    rr_name = iface_hostname,
                    rr_data = str(ip)
            )
            zo.add_rr(rr)


            # Test if current handled IP is the primary IP in the device. If
            # yes, CNAME the name of the device to this IP through the
            # iface_hostname value.

            # Get primary based on the interface object's associated device
            url = interface_obj['device']['url'] if interface_obj.get('device') else interface_obj['virtual_machine']['url']
            devvm: dict | None = netbox_query_obj(ctx, url)

            if devvm and devvm.get('primary_ip') and devvm['primary_ip'].get('address'):
                primary_ip: IPv4Interface | IPv6Interface = ip_interface(devvm['primary_ip']['address'])

                if ip == primary_ip.ip:
                    # Add CNAME towards primary ip_address holding interface
                    rr = DNS_Resource_Record(
                            rr_type = 'CNAME',
                            rr_name = dev_name,
                            rr_data = f"{iface_hostname}.{ctx['powerdns_rec_domain']}"
                            )
                    zo.add_rr(rr)

    return zo


def read_zonefile_footer_file(ctx: dict) -> str | None:
    # Inject footer file
    foot = None

    if (footer_filename := ctx.get('powerdns_rec_zonefile_footer')) and \
        len(footer_filename) > 0 and \
        (path := Path(footer_filename)) and \
        path.exists():

        with open(footer_filename, 'r') as f:
            foot = f.read()

    return foot


def write_zonefile(ctx: dict, zo: DNS_Zonefile, footer: str | None) -> None:

    # Write zonefile
    f = open(ctx['powerdns_rec_zonefile'], 'w')

    # Write the zonefile data to file
    f.write(str(zo))
    f.write("\n")

    # Add footer to zonefile
    if footer is not None:
        f.write(footer)

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

        # If the associated device or virtual machine is not active, skip
        status = get_status_of_devvm_from_ipaddresses_obj(ctx, ip_addr_obj)
        if status != 'active':
            print(f"skipping {ip_addr_obj['address']} because the device associated to the IP address is not active.")
            continue

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
            # print("Interface assigned to", ip_addr_obj['address'])
            if ip_addr_obj['address'] in net_vlan66.hosts():
                print("Interface assigned to", ip_addr_obj['address'], "is part of 192.168.1.0/24")
            continue


    # Write zonefile
    f = open(ctx['powerdns_rec_zonefile_in_addr'], 'w')

    # Write the zonefile data to file
    f.write(str(zo))
    f.write("\n")

    f.close()