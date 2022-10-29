#!/usr/bin/env python3

import os
import argparse
import configparser
import errno

### Sanity checks: on failure, makes no sense to continue
def sanity_checks(ctx):
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

    # Debug output
    if ctx['generic_verbose']:
        print('Authkey', ctx['generic_authkey'])
        print('Netbox base URL', ctx['generic_netbox_base_url'])
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

    args = parser.parse_args()

    ctx['args_verbose']                   = args.verbose
    ctx['args_configfile']                = args.configfile
    ctx['args_authkey']                   = args.authkey
    ctx['args_output_file']               = args.dnsmasq_dhcp_output_file
    ctx['args_netbox_base_url']           = args.netbox_base_url
    ctx['args_default_lease_time_range']  = args.dhcp_default_lease_time_range
    ctx['args_default_lease_time_host']   = args.dhcp_default_lease_time_host
    ctx['args_host_range_offset_min']     = args.dhcp_host_range_offset_min
    ctx['args_host_range_offset_max']     = args.dhcp_host_range_offset_max
    ctx['args_lease_file']                = args.dhcp_lease_file
    ctx['args_authoritive']               = args.dhcp_authoritive
    ctx['args_default_domain']            = args.dhcp_default_domain
    ctx['args_default_ntp_server']        = args.dhcp_default_ntp_server

    return ctx



def parse_config_section(ctx, config, section):
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


def parse_config(ctx):
    config = configparser.ConfigParser()

    if not os.path.isfile(ctx['args_configfile']):
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), ctx['args_configfile'])

    config.read(ctx['args_configfile'])

    ctx = parse_config_section(ctx, config, 'generic')
    ctx = parse_config_section(ctx, config, 'dnsmasq_dhcp')

    return ctx

