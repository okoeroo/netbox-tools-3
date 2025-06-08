DHCP config file like a canvas.
---

    DNSMasq_DHCP_Config is the main canvas
    Created per run

        DNSMasq_DHCP_Generic_Switchable (multiple on top)
        Created from config

        DNSMasq_DHCP_Section (multiple)
        Created from the fetched prefixed

            DNSMasq_DHCP_Option (multiple)
            Created from config

            DNSMasq_DHCP_Range (one)
            Created from netbox and the range associated to the handling prefix and with 'net_dhcp_range' tag
            Test: only one 'net_dhcp_range' per prefix or Error.

            DNSMasq_DHCP_Host (multiple)
            Created from netbox and fetches all ip addresses from all interfaces assigned with an IP address in the prefix of the section. The interface must be 'active'.
