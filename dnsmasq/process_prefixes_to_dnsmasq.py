#!/usr/bin/env python3

from dnsmasq import process_dnsmasq_sections
from netboxers import netboxers_helpers
from netboxers.models.dnsmasq_dhcp import DNSMasq_DHCP_Config, DNSMasq_DHCP_Generic_Switchable, DNSMasq_DHCP_Prefix


def filter_processing_of_prefix(ctx: dict, prefix_obj: DNSMasq_DHCP_Prefix) -> bool:
    """_summary_
        This is a filter to apply to a prefix to see if it must be filtered.

    Args:
        ctx (dict): _description_
        prefix_obj (DNSMasq_DHCP_Prefix): _description_

    Returns:
        bool: True means filter this prefix, False means don't filter.
    """

    if ctx.get('dnsmasq_dhcp_prefix_in_scope_by_tag'):
        tags = prefix_obj.get_tags()
        if not tags:
            return True
        if ctx.get('dnsmasq_dhcp_prefix_in_scope_by_tag') not in tags:
            return True

    if not prefix_obj.is_active():
        return True
        
    return False


def netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx: dict, dnsmasq_dhcp_config: DNSMasq_DHCP_Config) -> DNSMasq_DHCP_Config:
    # Get prefixes
    prefixes = netboxers_helpers.query_netbox(ctx, "ipam/prefixes/")

    if prefixes['count'] == 0:
        raise ValueError("No prefixes found in netbox to complete")

    # Select which prefixes to work on
    ready_to_process_prefixes: list[DNSMasq_DHCP_Prefix] = []
    for p in prefixes['results']:
        prefix_obj = DNSMasq_DHCP_Prefix(p)
        
        # Filter
        if filter_processing_of_prefix(ctx, prefix_obj):
            print(f"Notice: skipping prefix \"{prefix_obj.get_prefix()} due to configured filter constrains.")
            continue
        else:
            # Add to work list
            ready_to_process_prefixes.append(prefix_obj)
                
    # Work on these
    for p in ready_to_process_prefixes:
        # Use a DNSMasq_DHCP_Prefix to create a DNSMasq_DHCP_Section

        # Process the prefix. Output is a DNSMasq_DHCP_Section object
        dnsmasq_dhcp_section = process_dnsmasq_sections.netbox_process_prefix_into_dnsmasq_dhcp_section(ctx, p)
        if dnsmasq_dhcp_section is None:
            raise ValueError(f"Something happend processing the prefix {p.get_prefix()}")

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