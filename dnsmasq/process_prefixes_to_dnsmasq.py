#!/usr/bin/env python3

from dnsmasq import process_dnsmasq_sections
from netboxers import netboxers_helpers
from netboxers.models.dnsmasq_dhcp import DNSMasq_DHCP_Config, DNSMasq_DHCP_Generic_Switchable


def netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx: dict, dnsmasq_dhcp_config: DNSMasq_DHCP_Config) -> DNSMasq_DHCP_Config:
    # Get prefixes
    prefixes = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    if prefixes['count'] == 0:
        print("No prefixes found to complete")

    for prefix_obj in prefixes['results']:
        # Skip non-IPv4
        if prefix_obj['is_pool'] != True:
            continue

        # Only Active Prefixes
        if prefix_obj['status']['value'] != 'active':
            print("Prefix {} not active, skipping.".format(prefix_obj['prefix']))
            continue

        # Process the prefix. Output is a DNSMasq_DHCP_Section object
        dnsmasq_dhcp_section = process_dnsmasq_sections.netbox_process_prefix_into_dnsmasq_dhcp_section(ctx, prefix_obj)
        if dnsmasq_dhcp_section is None:
            raise f"Something happend processing the prefix {prefix_obj['prefix']}"

        # Record section to config
        dnsmasq_dhcp_config.append_to_dhcp_config_sections(dnsmasq_dhcp_section)
    
    return dnsmasq_dhcp_config
    

# This function will create a DNSMasq formatted DHCP config file from Netbox
## Create DNSMasq DHCP config file by:
## 1. Fetching defaults
## 2. Fetching VRFs, and VRF info.
## 3. Fetch associated default gateway and DNS config
## 4. Fetch (virtual) hosts and its data (IP and MAC)

def netbox_to_dnsmasq_dhcp_config(ctx: dict):
    # Create DNSMasq DHCP config
    dnsmasq_dhcp_config = DNSMasq_DHCP_Config()

    # File header: set dhcp-leasefile
    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("dhcp-leasefile", ctx['dnsmasq_dhcp_lease_file']))

    # File header: set authoritive DHCP
    if ctx['dnsmasq_dhcp_authoritive']:
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-authoritative", None))

    # File header: set default domain
    dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
            DNSMasq_DHCP_Generic_Switchable("domain", ctx['dnsmasq_dhcp_default_domain']))

    # File header: set PXE boot filename, servername and address
    if 'dnsmasq_dhcp_boot_filename' in ctx:
        dhcp_boot_elems = []
        dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_filename'])
        if 'dnsmasq_dhcp_boot_servername' in ctx:
            dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_servername'])
        if 'dnsmasq_dhcp_boot_address' in ctx:
            dhcp_boot_elems.append(ctx['dnsmasq_dhcp_boot_address'])
        
        # Join the elements together with comma-delimeter
        dhcp_boot = ','.join(dhcp_boot_elems)

        # Finalize the configuration
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", dhcp_boot))

        ### HACK Add PXE boot hacks
        # inspect the vendor class string and match the text to set the tag
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-vendorclass", "BIOS,PXEClient:Arch:00000"))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-vendorclass", "UEFI32,PXEClient:Arch:00006"))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-vendorclass", "UEFI,PXEClient:Arch:00007"))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-vendorclass", "UEFI64,PXEClient:Arch:00009"))

        # Set the boot file name based on the matching tag from the vendor class (above)
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", "net:UEFI32," + dhcp_boot))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", "net:BIOS," + dhcp_boot))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", "net:UEFI64," + dhcp_boot))
        dnsmasq_dhcp_config.append_to_dhcp_config_generic_switches(
                DNSMasq_DHCP_Generic_Switchable("dhcp-boot", "net:UEFI," + dhcp_boot))

    # Get prefixes and process each
    dnsmasq_dhcp_config = netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx, dnsmasq_dhcp_config)

    # Truncate and open file cleanly
    netboxers_helpers.write_to_ddo_fh(ctx, None)

    ## Output DNSMasq Config to file
    netboxers_helpers.write_to_ddo_fh(ctx, str(dnsmasq_dhcp_config))