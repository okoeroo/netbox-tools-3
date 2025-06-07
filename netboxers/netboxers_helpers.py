#!/usr/bin/env python3

import os
import pprint
import re
import ipaddress
import dns.rdataclass
from dns import rdataclass
import requests
import dns


# All non-alfanum, replace with underscore and lowercase it
# Used to create a interface + device name combo.
def sanitize(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '_', s).lower()


def make_host_iface_name(dev_name: str, if_name: str) -> str:
    return f"{sanitize(dev_name)}_{sanitize(if_name)}"


def make_iface_dot_host_name(dev_name: str, if_name: str) -> str:
    return f"{sanitize(if_name)}.{sanitize(dev_name)}"


def pp(obj):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(obj)


def test_write_to_ddo_fh(ctx: dict):
    # Truncate file
    if ctx['dnsmasq_dhcp_output_file'] is not None:
        open(ctx['dnsmasq_dhcp_output_file'], 'w').close()
        return


def write_to_ddo_fh(ctx: dict, s: str | None):
    # Truncate file
    if s is None and ctx['dnsmasq_dhcp_output_file'] is not None:
        open(ctx['dnsmasq_dhcp_output_file'], 'w').close()
        return

    # Print or write
    if ctx['dnsmasq_dhcp_output_file'] is None:
        print(s)
    else:
        with open(ctx['dnsmasq_dhcp_output_file'], 'a') as the_file:
            if s is None:
                the_file.write(os.linesep)
            else:
                the_file.write(s + os.linesep)


def normalize_name(name: str):
    return name.lower().replace(" ", "_").replace("-", "_").replace("\"", "").replace("\'", "")


def dns_canonicalize(s: str):
    if not s.endswith('.'):
        return s + '.'
    else:
        return

def get_ctx():
    ctx = {}
    return ctx

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


def add_rr_to_zone(ctx: dict, zone, rr_obj):
    if 'name' not in rr_obj:
        raise ValueError("rr_obj missing name")

    if 'type' not in rr_obj:
        raise ValueError("rr_obj missing type")

    if 'ttl' not in rr_obj:
        rr_obj['ttl'] = 86400

    rdclass = dns.rdataclass._by_text.get('IN')

    # A
    if rr_obj['type'] == 'A': 
        if 'name' not in rr_obj or 'type' not in rr_obj or 'data' not in rr_obj:
            raise ValueError("rr_obj missing elements for A record")

        rdtype = dns.rdatatype._by_text.get(rr_obj['type'])
        rdataset = zone.find_rdataset(rr_obj['name'], rdtype=rdtype, create=True)
        rdata = dns.rdata.from_text(rdclass, rdtype, rr_obj['data'])
        rdataset.add(rdata, ttl=rr_obj['ttl'])
        return

    # PTR
    if rr_obj['type'] == 'PTR': 
        if 'name' not in rr_obj or 'type' not in rr_obj or 'data' not in rr_obj:
            raise ValueError("rr_obj missing elements for A record")

        rdtype = dns.rdatatype._by_text.get(rr_obj['type'])
        rdataset = zone.find_rdataset(rr_obj['name'], rdtype=rdtype, create=True)
        rdata = dns.rdata.from_text(rdclass, rdtype, rr_obj['data'])
        rdataset.add(rdata, ttl=rr_obj['ttl'])
        return

    # CNAME
    if rr_obj['type'] == 'CNAME': 
        if 'name' not in rr_obj or 'type' not in rr_obj or 'data' not in rr_obj:
            raise ValueError("rr_obj missing elements for CNAME record")

        rdtype = dns.rdatatype._by_text.get(rr_obj['type'])
        rdataset = zone.find_rdataset(rr_obj['name'], rdtype=rdtype, create=True)
        rdata = dns.rdata.from_text(rdclass, rdtype, rr_obj['data'])
        rdataset.add(rdata, ttl=rr_obj['ttl'])
        return

    # SOA
    if rr_obj['type'] == 'SOA':
        if 'name' not in rr_obj or 'type' not in rr_obj or \
            'mname' not in rr_obj or 'rname' not in rr_obj:
            raise ValueError("rr_obj missing elements for SOA record")

        rdtype = dns.rdatatype._by_text.get(rr_obj['type'])
        rdataset = zone.find_rdataset(rr_obj['name'], rdtype=rdtype, create=True)
        rdata = dns.rdtypes.ANY.SOA.SOA(rdclass, rdtype,
                    mname = dns.name.Name(rr_obj['mname'].split('.')),
                    rname = dns.name.Name(rr_obj['rname'].split('.')),
                    serial = rr_obj['serial'],
                    refresh = rr_obj['refresh'],
                    retry = rr_obj['retry'],
                    expire = rr_obj['expire'],
                    minimum = rr_obj['minimum']
        )
        rdataset.add(rdata, ttl=rr_obj['ttl'])
        return

    # NS
    if rr_obj['type'] == 'NS':
        rdtype = dns.rdatatype._by_text.get(rr_obj['type'])
        rdataset = zone.find_rdataset(rr_obj['name'], rdtype=rdtype, create=True)

        if rr_obj['data'][-1:] != '.':
             rr_obj['data'] = rr_obj['data'] + '.'

        rdata = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.NS,
                                 rr_obj['data'])

        rdataset.add(rdata, ttl=rr_obj['ttl'])


### Cleanup hostname. Examples:
### hostname_eth0.1 => hostname_eth0__1
### hostname_eth0:1 => hostname_eth0___1
def dnsmasq_hostname_cleanup(raw_hostname: str) -> str:
    return raw_hostname.replace(":", "___").replace(".", "__")


######### begin of dead code
def is_ipaddress(to_check):
    try:
        ipaddress.ip_address(to_check)
        return True
    except Exception as err:
        return False

def is_valid_macaddr802(value):
    allowed = re.compile(r"""
                         (
                             ^([0-9A-F]{2}[-]){5}([0-9A-F]{2})$
                            |^([0-9A-F]{2}[:]){5}([0-9A-F]{2})$
                         )
                         """,
                         re.VERBOSE|re.IGNORECASE)

    if allowed.match(value) is None:
        return False
    else:
        return True
