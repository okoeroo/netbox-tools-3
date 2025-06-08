#!/usr/bin/env python3

from dnsmasq.process_dnsmasq_sections import netbox_process_prefix_into_dnsmasq_dhcp_section
from netboxers.netboxers_helpers import write_data_to_file
from netboxers.netboxers_queries import fetch_active_prefixes
from netboxers.models.netbox import Netbox_Prefix
from netboxers.models.dnsmasq_dhcp import DNSMasq_DHCP_Config, DNSMasq_DHCP_Generic_Switchable


def netbox_process_prefixes_into_dnsmasq_dhcp_config(ctx: dict, dnsmasq_dhcp_config: DNSMasq_DHCP_Config) -> DNSMasq_DHCP_Config:
    # Select which prefixes to work on
    active_prefixes: list[Netbox_Prefix] = fetch_active_prefixes(ctx)
    dhcp_prefix_tag = ctx.get('dnsmasq_dhcp_prefix_in_scope_by_tag') 
    if dhcp_prefix_tag:
        ready_to_process_prefixes = [prefix for prefix in active_prefixes 
                                                if prefix.get_tags() and dhcp_prefix_tag in prefix.get_tags()]
    else:
        ready_to_process_prefixes = active_prefixes

   
    # Work on these
    for p in ready_to_process_prefixes:
        # Use a Netbox_Prefix to create a DNSMasq_DHCP_Section

        # Process the prefix. Output is a DNSMasq_DHCP_Section object
        dnsmasq_dhcp_section = netbox_process_prefix_into_dnsmasq_dhcp_section(ctx, p)
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

    ## Output DNSMasq Config to file
    write_data_to_file(ctx.get('dnsmasq_dhcp_output_file'), str(dnsmasq_dhcp_config))