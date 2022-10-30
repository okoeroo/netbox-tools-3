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

    if 'powerdns_rec_zonefile' not in ctx or ctx['powerdns_rec_zonefile'] is None:
        print("No PowerDNS Recursor output file configured. Use command line CLI flags or \"zonefile\" in the configuration file\"")
        return False

    if 'powerdns_rec_zonefile_in_addr' not in ctx or ctx['powerdns_rec_zonefile_in_addr'] is None:
        print("No PowerDNS Recursor output file configured. Use command line CLI flags or \"zonefile_in_addr\" in the configuration file\"")
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
    parser.add_argument("-bu", "--base-url",
                        dest='netbox_base_url',
                        help="Netbox base URL.",
                        default=None,
                        type=str)

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

    parser.add_argument("-f", "--zonefooter",
                        dest='powerdns_rec_zonefooter',
                        help="Zonefile footer template.",
                        default=None,
                        type=str)

    args = parser.parse_args()

    ctx['args_verbose']                   = args.verbose
    ctx['args_configfile']                = args.configfile
    ctx['args_authkey']                   = args.authkey
    ctx['args_netbox_base_url']           = args.netbox_base_url

    ctx['args_zonefile']                  = args.powerdns_rec_zonefile
    ctx['args_zonefile_in_addr']          = args.powerdns_rec_zonefile_in_addr
    ctx['args_zonefile_relativize']       = args.powerdns_rec_zonefile_relativize
    ctx['args_zonefooter']                = args.powerdns_rec_zonefooter

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
    ctx = parse_config_section(ctx, config, 'powerdns_rec')

    return ctx

