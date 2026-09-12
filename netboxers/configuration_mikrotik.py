#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import errno
import ipaddress



### Sanity checks: on failure, makes no sense to continue
def sanity_checks(ctx):
    # Checks
    if ctx['generic_authkey'] is None:
        print("No Netbox authentication key provided")
        return False

    if ctx['generic_netbox_base_url'] is None:
        print("No Netbox base URL provided")
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
                        default="netbox-mikrotik.config",
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

    args = parser.parse_args()

    # Generic
    ctx['args_verbose']                         = args.verbose
    ctx['args_configfile']                      = args.configfile
    ctx['args_authkey']                         = args.authkey
    ctx['args_netbox_base_url']                 = args.netbox_base_url

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
    ctx = parse_config_section(ctx, config, 'mikrotik')
    ctx = parse_config_section(ctx, config, 'dhcpv4')

    return ctx

