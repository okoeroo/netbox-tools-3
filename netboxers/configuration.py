#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import errno
import ipaddress



### Sanity checks: on failure, makes no sense to continue
def sanity_checks(ctx):
    # Defaults
    if not ctx.get('dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'):
        ctx['dnsmasq_dhcp_default_gateway_per_prefix_identified_by_tag'] = 'net_default_gateway'
    
    if not ctx.get('dnsmasq_dhcp_selected_range_in_prefix_by_tag'):
        ctx['dnsmasq_dhcp_selected_range_in_prefix_by_tag'] = 'net_dhcp_range'

    # Checks
    if ctx['generic_authkey'] is None:
        print("No Netbox authentication key provided")
        return False

    if ctx['generic_netbox_base_url'] is None:
        print("No Netbox base URL provided")
        return False

    if 'dnsmasq_dhcp_output_file' not in ctx or ctx['dnsmasq_dhcp_output_file'] is None:
        print("No DNSMasq DHCP output file configured. Use command line CLI flags or \"dnsmasq_dhcp_output_file\" in the configuration file\"")
        return False

    #auto-correct base URL
    if ctx['generic_netbox_base_url'].endswith('/'):
        ctx['generic_netbox_base_url'] = ctx['generic_netbox_base_url'][:-1]

    if not ctx['generic_netbox_base_url'].startswith('http://') and \
        not ctx['generic_netbox_base_url'].startswith('https://'):
        print("The provided base URL does not start with http:// or https://. Value:",
            ctx['generic_netbox_base_url'])
        sys.exit(1)

    # Override DNS Server
    if 'dnsmasq_dhcp_override_dns_server' in ctx and ctx['dnsmasq_dhcp_override_dns_server'] is not None:
        try:
            ipaddress.ip_address(ctx['dnsmasq_dhcp_override_dns_server'])
        except ipaddress.AddressValueError:
            print(f"Error: this is not a proper IP address: {ctx['dnsmasq_dhcp_override_dns_server']}")
            sys.exit(1)

        ctx['dnsmasq_dhcp_override_dns_server'] = ipaddress.ip_address(ctx['dnsmasq_dhcp_override_dns_server'])


    if 'powerdns_rec_zonefile' not in ctx or ctx['powerdns_rec_zonefile'] is None:
        print("No PowerDNS Recursor output file configured. Use command line CLI flags or \"zonefile\" in the configuration file\"")
        return False

    if 'powerdns_rec_zonefile_in_addr' not in ctx or ctx['powerdns_rec_zonefile_in_addr'] is None:
        print("No PowerDNS Recursor output file configured. Use command line CLI flags or \"zonefile_in_addr\" in the configuration file\"")
        return False


    # Debug output
    if ctx['generic_verbose']:
        print('Authkey', ctx['generic_authkey'])
        print('Netbox base URL', ctx['generic_netbox_base_url'])
        print('Override DNS server', ctx['dnsmasq_dhcp_override_dns_server'])
        print()
    return True


def argparsing(ctx):
    # Parser
    parser = argparse.ArgumentParser(os.path.basename(__file__))
    parser.add_argument("-v", "--verbose",
                        dest='verbose',
                        help="Verbose mode. Default is off",
                        action="store_true",
                        default=False)
    parser.add_argument("-c", "--config",
                        dest='configfile',
                        help="Configuration file.",
                        default="netbox.config",
                        type=str)
    parser.add_argument("-k", "--authkey",
                        dest='authkey',
                        help="Netbox authentication key.",
                        default=None,
                        type=str)
    parser.add_argument("-do", "--dnsmasq-dhcp-output-file",
                        dest='dnsmasq_dhcp_output_file',
                        help="DNSMasq format DHCP output file based on Netbox info.",
                        default=None,
                        type=str)
    parser.add_argument("-bu", "--base-url",
                        dest='netbox_base_url',
                        help="Netbox base URL.",
                        default=None,
                        type=str)

    # DNSMasq DHCP
    parser.add_argument("-ltr", "--dhcp-default-lease-time-range",
                        dest='dhcp_default_lease_time_range',
                        help="DHCP Default Lease Time for a DHCP range.",
                        default=None,
                        # default="12h",
                        type=str)
    parser.add_argument("-lth", "--dhcp-default-lease-time-host",
                        dest='dhcp_default_lease_time_host',
                        help="DHCP Default Lease Time for a fixed DCHP host.",
                        default=None,
                        # default="600m",
                        type=str)
    parser.add_argument("-min", "--dhcp-host-range-offset-min",
                        dest='dhcp_host_range_offset_min',
                        help="DHCP Host range offset minimum.",
                        default=None,
                        # default=100,
                        type=int)
    parser.add_argument("-max", "--dhcp-host-range-offset-max",
                        dest='dhcp_host_range_offset_max',
                        help="DHCP Host range offset maximum.",
                        default=None,
                        # default=199,
                        type=int)
    parser.add_argument("-dn", "--dhcp-default-ntp-server",
                        dest='dhcp_default_ntp_server',
                        help="Default NTP server distribute via DHCP.",
                        default=None,
                        type=str)
    parser.add_argument("-lf", "--dhcp-lease-file",
                        dest='dhcp_lease_file',
                        help="DHCP Lease file.",
                        default=None,
                        # default="/var/cache/dnsmasq/dnsmasq-dhcp.leasefile",
                        type=str)
    parser.add_argument("-da", "--dhcp-authoritive",
                        dest='dhcp_authoritive',
                        help="Set DHCP Authoritive flag",
                        action="store_true",
                        default=None)
                        # default=True)
    parser.add_argument("-ddd", "--dhcp-default-domain",
                        dest='dhcp_default_domain',
                        help="DHCP Default Domain.",
                        default=None,
                        # default="koeroo.lan",
                        type=str)
    parser.add_argument("-dds", "--dhcp-domain-search",
                        dest='dhcp_domain_search',
                        help="DHCP Domain Search.",
                        default=None,
                        # default="koeroo.lan",
                        type=str)
    parser.add_argument("-dbf", "--dhcp-boot-filename",
                        dest='dhcp_boot_filename',
                        help="DHCP PXE boot filename.",
                        default=None,
                        type=str)
    parser.add_argument("-dbs", "--dhcp-boot-servername",
                        dest='dhcp_boot_servername',
                        help="DHCP PXE boot servername.",
                        default=None,
                        type=str)
    parser.add_argument("-dba", "--dhcp-boot-address",
                        dest='dhcp_boot_address',
                        help="DHCP PXE boot address.",
                        default=None,
                        type=str)
    parser.add_argument("-ods", "--override-dns-server",
                        dest='override_dns_server',
                        help="Override DNS Server configuration with provided IP address",
                        default=None,
                        type=str)
    parser.add_argument("-pit", "--prefix-in-scope-by-tag",
                        dest='prefix_in_scope_by_tag',
                        help="Add all prefixes, unless scoped by finding this set tag name to a prefix",
                        default=None,
                        type=str)
    parser.add_argument("-dgpt", "--default-gateway-per-prefix-identified-by-tag",
                        dest='default_gateway_per_prefix_identified_by_tag',
                        help="Selector of the default gateway per prefix. The IP address of the default gateway is identified by the configured tag name. Recommended is to use \'net_default_gateway\'",
                        default=None,
                        type=str)
    parser.add_argument("-srpt", "--selected-range-in-prefix-by-tag",
                        dest='selected_range_in_prefix_by_tag',
                        help="Selector range in prefix by tag.",
                        default=None,
                        type=str)

    # PowerDNS specific
    parser.add_argument("-d", "--domain",
                        dest='powerdns_rec_domain',
                        help="Domain to be used in the configuration for forward and reverse lookup configurations.",
                        default=None,
                        type=str)
    parser.add_argument("-z", "--zonefile",
                        dest='powerdns_rec_zonefile',
                        help="Zonefile format to be consumed by Bind or PowerDNS.",
                        default=None,
                        type=str)
    parser.add_argument("-zia", "--zonefile-in-addr",
                        dest='powerdns_rec_zonefile_in_addr',
                        help="Zonefile format to be consumed by Bind or PowerDNS, but specifically for the reverse lookups.",
                        default=None,
                        type=str)
    parser.add_argument("-rl", "--relativize",
                        dest='powerdns_rec_zonefile_relativize',
                        help="Create relativized names in the zonefile",
                        action="store_true",
                        default=True)

    parser.add_argument("-f", "--zone-footer",
                        dest='powerdns_rec_zonefile_footer',
                        help="Zonefile footer template.",
                        default=None,
                        type=str)




    args = parser.parse_args()

    # Generic
    ctx['args_verbose']                         = args.verbose
    ctx['args_configfile']                      = args.configfile
    ctx['args_authkey']                         = args.authkey
    
    # DNSMasq DHCP
    ctx['args_output_file']                     = args.dnsmasq_dhcp_output_file
    ctx['args_netbox_base_url']                 = args.netbox_base_url
    ctx['args_default_lease_time_range']        = args.dhcp_default_lease_time_range
    ctx['args_default_lease_time_host']         = args.dhcp_default_lease_time_host
    ctx['args_host_range_offset_min']           = args.dhcp_host_range_offset_min
    ctx['args_host_range_offset_max']           = args.dhcp_host_range_offset_max
    ctx['args_lease_file']                      = args.dhcp_lease_file
    ctx['args_authoritive']                     = args.dhcp_authoritive
    ctx['args_default_domain']                  = args.dhcp_default_domain
    ctx['args_domain_search']                   = args.dhcp_domain_search
    ctx['args_default_ntp_server']              = args.dhcp_default_ntp_server
    ctx['args_dhcp_boot_filename']              = args.dhcp_boot_filename
    ctx['args_dhcp_boot_servername']            = args.dhcp_boot_servername
    ctx['args_dhcp_boot_address']               = args.dhcp_boot_address
    ctx['args_override_dns_server']             = args.override_dns_server
    ctx['args_prefix_in_scope_by_tag']          = args.prefix_in_scope_by_tag
    ctx['args_default_gateway_per_prefix_identified_by_tag'] = args.default_gateway_per_prefix_identified_by_tag
    ctx['args_selected_range_in_prefix_by_tag'] = args.selected_range_in_prefix_by_tag

    # PowerDNS Rec
    ctx['args_zonefile']                        = args.powerdns_rec_zonefile
    ctx['args_zonefile_in_addr']                = args.powerdns_rec_zonefile_in_addr
    ctx['args_zonefile_relativize']             = args.powerdns_rec_zonefile_relativize
    ctx['args_zonefile_footer']                 = args.powerdns_rec_zonefile_footer


    return ctx


def parse_config_section(ctx: dict, config, section):
    if section not in config.sections():
        print(f"Warning: Configuration file does not have a \"{section}\" section")
        return ctx

    for key in config[section]:
        if 'args_' + key in ctx and ctx['args_' + key] is not None:
            ctx[section + "_" + key] = ctx['args_' + key]
            continue
        else:
            ctx[section + "_" + key] = config[section][key]

    return ctx


# Look for all [prefix:<cidr>]
def parse_config_prefixes(ctx, config):
    # init prefixes overrides
    ctx['prefixes'] = {}

    # Dynamically load prefix information into the ctx
    for section in config.sections():
        if section.startswith("prefix:"):
            prefix = section.split(":")[1] 
            ctx['prefixes'][prefix] = {}
            for key in config[section]:
                ctx['prefixes'][prefix][key] = config[section][key]

    return ctx


def parse_config(ctx: dict) -> dict:
    config = configparser.ConfigParser()

    if not os.path.isfile(ctx['args_configfile']):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), ctx['args_configfile'])

    config.read(ctx['args_configfile'])

    ctx = parse_config_section(ctx, config, 'generic')
    ctx = parse_config_section(ctx, config, 'dnsmasq_dhcp')
    ctx = parse_config_section(ctx, config, 'powerdns_rec')
    ctx = parse_config_prefixes(ctx, config)

    return ctx

