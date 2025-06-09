from pathlib import Path
import ipaddress
from ipaddress import IPv4Address, IPv6Address, IPv4Interface, IPv6Interface, ip_interface, ip_address

from netboxers.netboxers_helpers import make_iface_dot_host_name, write_data_to_file
from netboxers.netboxers_queries import cache_netbox_query_list, \
                                        get_status_of_devvm_from_ipaddresses_obj_from_dev_vm_list, \
                                        get_hosts_from_prefix, \
                                        fetch_active_prefixes
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


def get_device_or_virtualmachine_obj(ctx: dict, interface_obj: dict) -> dict | None:
    # Get device or virtualmachine object associated to the interface object.

    for key, cache_key in [
            ('device', 'dcim/devices/'),
            ('virtual_machine', 'virtualization/virtual-machines/')
        ]:
        if obj := interface_obj.get(key):
            return next((d for d in ctx['cache'][cache_key] if d['id'] == obj['id']), None)
    return None


def get_primary_ip_from_interface(ctx: dict, interface_obj: dict) -> IPv4Interface | IPv6Interface | None:
    # get primary IP address from the interface (through the device configuration)
    devvm = get_device_or_virtualmachine_obj(ctx, interface_obj)
    if devvm and (p_ip := devvm.get('primary_ip')) and (addr := p_ip.get('address')):
        return ip_interface(addr)
    return None


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

            primary_ip = get_primary_ip_from_interface(ctx, interface_obj)

            if primary_ip and ip == primary_ip.ip:
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
    l = []
    l.append(str(zo))
    if footer:
        l.append(footer)

    s = "\n\n".join(l)

    # Write zonefile
    write_data_to_file(ctx['powerdns_rec_zonefile'], s)
    


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

    # Fetch all devices
    unfiltered_devices = cache_netbox_query_list(ctx, "dcim/devices")
    if unfiltered_devices:
        devices = [d for d in unfiltered_devices if d['status']['value'] in ('active', 'decommissioning', 'staged')]
    else:
        devices = None

    # Fetch all virtual machines
    unfiltered_vms = cache_netbox_query_list(ctx, "virtualization/virtual-machines/")
    if unfiltered_vms:
        vms = [d for d in unfiltered_vms if d['status']['value'] in ('active', 'decommissioning', 'staged')]
    else:
        vms = None


    # Query for prefixes and ranges
    ip_addresses = cache_netbox_query_list(ctx, "ipam/ip-addresses/")
    if not ip_addresses:
        print("Error: no IP addresses found.")
        return

    # Filter on active and reserved IP addresses
    ip_addresses_to_process = [ip for ip in ip_addresses if ip['status']['value'] in ('active', 'reserved')]
                                     
    # Process
    for ip_addr_obj in ip_addresses_to_process:
        if ip_addr_obj['family']['value'] == 6:
            print(f"IP address {ip_addr_obj['address']} skipping IPv6 for PTR records.")
            continue

        ip = ip_interface(ip_addr_obj['address'])
        if not ip.is_private:
            print(f"IP address {ip_addr_obj['address']} skipping because not RFC1918.")
            continue
        

        # Handle reserved
        # Will create a new DNS Resource Record with the IP address and reserved tag.
        if ip_addr_obj['status']['value'] == 'reserved': 
            rr = create_rr_ptr_for_reserved_address(ip_addr_obj['address'], "reserved_ip")
            zo.add_rr(rr)
            continue
        
        
        # If the associated device or virtual machine is not active, skip
        status = get_status_of_devvm_from_ipaddresses_obj_from_dev_vm_list(ctx, ip_addr_obj, devices, vms)
        if status is None:
            print(f"skipping {ip_addr_obj['address']} as there is no interface assigned to it.")
            continue
        elif status != 'active':
            print(f"skipping {ip_addr_obj['address']} because the device associated to the IP address is not active.")
            continue

        # Create DNS Resource Record from IP address information
        rr = create_rr_ptr_from_ip_address(ctx, ip_addr_obj)
        zo.add_rr(rr)


    ## Create PTR records for IP Range addresses.
    ip_ranges = cache_netbox_query_list(ctx, "ipam/ip-ranges/")
    if not ip_ranges:
        print("Warning: no IP addresses found.")
    else:
        for ip_range in ip_ranges:
            for ip in ip_range_iterator(ip_range['start_address'], ip_range['end_address']):
                rr = create_rr_ptr_for_reserved_address(ip, "range_ip")
                zo.add_rr(rr)


    # Write zonefile
    write_data_to_file(ctx.get('powerdns_rec_zonefile_in_addr'), str(zo))


def ip_range_iterator(start: str, end: str):
    start_ip = ip_interface(start)
    end_ip = ip_interface(end)
    for ip_int in range(int(start_ip.ip), int(end_ip.ip) + 1):
        yield ip_address(ip_int)


def is_ip_interface(s: str) -> bool:
    ip = ip_interface(s)
    return ip.network.prefixlen != ip.max_prefixlen


def create_rr_ptr_for_reserved_address(ip_addr: IPv4Address | IPv6Address | str,
                                       prefix_name: str) -> DNS_Resource_Record:
    def sanitize_ip(ip_obj: IPv4Address | IPv6Address) -> str:
        return str(ip_obj).replace('.', '_').replace(':', '_')
    
    # Reverse the IP address, and it's complicated due to accepting both str and IPv{4,6}Address
    if type(ip_addr) is IPv4Address or type(ip_addr) is IPv6Address:
        rev_ip_addr = ip_addr.reverse_pointer
        flatten_ip = sanitize_ip(ip_addr)
    elif type(ip_addr) is str:
        if is_ip_interface(ip_addr):
            interface = ip_interface(ip_addr)
            rev_ip_addr = interface.ip.reverse_pointer
            flatten_ip = sanitize_ip(interface.ip)
        else:
            ip = ip_address(ip_addr)
            rev_ip_addr = ip.reverse_pointer
            flatten_ip = sanitize_ip(ip)
    else:
        raise ValueError("Error in converting {ip_addr}")

    flatten_data = f"{prefix_name}_{flatten_ip}"

    rr = DNS_Resource_Record(
            rr_type = 'PTR',
            rr_name = rev_ip_addr,
            rr_data = flatten_data)
    
    return rr
    

def create_rr_ptr_from_ip_address(ctx: dict, ip_addr_obj: dict) -> DNS_Resource_Record:
    tupple = {}

    # Assemble the tupple
    tupple['ip_addr'] = ip_addr_obj['address']

    if 'device' in ip_addr_obj['assigned_object']:
        tupple['host_name'] = ip_addr_obj['assigned_object']['device']['name']
    elif 'virtual_machine' in ip_addr_obj['assigned_object']:
        tupple['host_name'] = ip_addr_obj['assigned_object']['virtual_machine']['name']

    tupple['interface_name'] = ip_addr_obj['assigned_object']['name']

    ip_addr_interface = ipaddress.ip_interface(tupple['ip_addr'])
    tupple['rev_ip_addr'] = ip_addr_interface.ip.reverse_pointer


    # RFC compliant domain name
    iface_hostname = make_iface_dot_host_name(tupple['host_name'], tupple['interface_name'])
    rfc_host_name = f"{iface_hostname}.{ctx['powerdns_rec_domain']}"

    rr = DNS_Resource_Record(
            rr_type = 'PTR',
            rr_name = tupple['rev_ip_addr'],
            rr_data = rfc_host_name)
    
    return rr