
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network, ip_network


class DNSMasq_DHCP_Prefix:
    def __init__(self, data: dict):
        self.data: dict = data
        self.prefix: IPv4Network | IPv6Network = ip_network(self.data['prefix'], strict=True)
    
    def get_prefix(self) -> IPv4Network | IPv6Network:
        return self.prefix

    def get_vrf(self) -> dict | None:
        return self.data.get('vrf')
            
    def get_scope(self) -> dict | None:
        return self.data.get('scope')

    def get_site(self) -> str | None:
        if scope := self.data.get('scope'):
            return scope['name']

    def get_vlan(self) -> dict | None:
        return self.data.get('vlan')

    def get_status(self) -> dict:
        return self.data['status']['value']

    def is_active(self) -> bool:
        return self.get_status() == 'active'
    
    def get_role(self) -> dict | None:
        return self.data.get('role')

    def is_pool(self) -> bool:
        return self.data['is_pool']

    def get_tags(self) -> list[str] | None:
        tags = self.data.get('tags')
        if not tags: return None
        return [t.get('name') for t in tags]


class DNSMasq_DHCP_Generic_Switchable:
    def __init__(self, name: str, value: str | None):
        self.name = name
        self.value = value

    def __str__(self) -> str:
        if self.value is None:
            return self.name
        else:
            return f"{self.name}={self.value}"


class DNSMasq_DHCP_Option:
    def __init__(self, prefix: DNSMasq_DHCP_Prefix, option: str, value: str):
        if not prefix:
            raise ValueError("DNSMasq_DHCP_Option requires a DNSMasq_DHCP_Prefix")
            
        self.prefix: DNSMasq_DHCP_Prefix    = prefix
        self.option: str                    = option
        self.value: str                     = value

    def get_prefix(self) -> DNSMasq_DHCP_Prefix:
        return self.prefix

    def get_option(self) -> str:
        return self.option

    def get_value(self) -> str | IPv4Address | IPv6Address:
        return self.value

    def get_comment(self) -> str:
        match self.get_option():
            case "3":
                return "# Default Gateway"    
            case "6":
                return "# Default DNS"
            case "42":
                return "# Default NTP"
            case "119":
                return "# Domain Search"
            case _:
                return ""

    def __add__(self, o):
        return self.get_str() + o

    def __str__(self):
        return self.get_str()

    # dhcp-option=vrf_66_homelan_vlan_66,3,192.168.1.1  # Default Gateway
    def get_str(self) -> str:
        res = []

        prefix = self.get_prefix()
        if vrf:= prefix.get_vrf():
            res.append(vrf['name'])

        res.append(str(self.get_option()))
        res.append(str(self.get_value()))

        return f"dhcp-option={",".join(res)}  {self.get_comment()}"


class DNSMasq_DHCP_Range:
    def __init__(self, 
                 prefix: DNSMasq_DHCP_Prefix,
                 range_min: IPv4Address | IPv6Address, 
                 range_max: IPv4Address | IPv6Address, 
                 netmask: IPv4Address | IPv6Address, 
                 lease_time: str):
        self.prefix: DNSMasq_DHCP_Prefix = prefix
        self.range_min: IPv4Address | IPv6Address = range_min
        self.range_max: IPv4Address | IPv6Address = range_max
        self.netmask: IPv4Address | IPv6Address = netmask
        self.lease_time: str = lease_time

    def get_prefix(self) -> DNSMasq_DHCP_Prefix:
        return self.prefix

    def get_range_min(self):
        return self.range_min

    def get_range_max(self):
        return self.range_max

    def get_netmask(self):
        return self.netmask

    def get_lease_time(self):
        return self.lease_time

    def __add__(self, o):
        return self.get_str() + o

    def __str__(self):
        return self.get_str()

    def get_str(self):
        res = []

        prefix = self.get_prefix()
        if vrf:= prefix.get_vrf():
            res.append(vrf['name'])

        res.append(str(self.get_range_min()))
        res.append(str(self.get_range_max()))
        res.append(str(self.get_netmask()))
        res.append(str(self.get_lease_time()))

        return f"dhcp-range={",".join(res)}"


class DNSMasq_DHCP_Host:
    def __init__(self, 
                 prefix: DNSMasq_DHCP_Prefix,
                 mac_address: str, 
                 hostname: str, 
                 ip_address: str | IPv4Address | IPv6Address, 
                 lease_time: str):
        self.prefix = prefix
        self.mac_address = mac_address
        self.hostname = hostname
        self.ip_address = ip_address
        self.lease_time = lease_time

    def get_prefix(self):
        return self.prefix

    def get_mac_address(self):
        return self.mac_address

    def get_hostname(self):
        return self.hostname

    def get_ip_address(self):
        return self.ip_address

    def get_lease_time(self):
        return self.lease_time

    def __add__(self, o):
        return self.get_str() + o

    def __str__(self):
        return self.get_str()

    def get_str(self):
        res = []

        prefix = self.get_prefix()
        if vrf:= prefix.get_vrf():
            res.append(vrf['name'])

        res.append(str(self.get_mac_address()))
        res.append(str(self.get_hostname()))
        res.append(str(self.get_ip_address()))
        res.append(str(self.get_lease_time()))

        return f"dhcp-host={",".join(res)}"


class DNSMasq_DHCP_Section:
    def __init__(self, prefix_obj: DNSMasq_DHCP_Prefix):
        self.scope = prefix_obj.get_scope()
        self.site = prefix_obj.get_site()
        self.role = prefix_obj.get_role()
        self.vlan_id = None
        self.vlan_name = None
        if vlan := prefix_obj.get_vlan():
            self.vlan_id = vlan['vid']
            self.vlan_name = vlan['display']

        if vrf := prefix_obj.get_vrf():
            self.vrf_name = vrf['name']

        self.prefix = prefix_obj.get_prefix()

        self.dhcp_options: list[DNSMasq_DHCP_Option] = []
        self.dhcp_ranges: list[DNSMasq_DHCP_Range] = []
        self.dhcp_hosts: list[DNSMasq_DHCP_Host] = []

    def set_scope(self, scope):
        self.scope = scope

    def set_role(self, role):
        self.role = role

    def set_vlan_id(self, vlan_id):
        self.vlan_id = vlan_id

    def set_vlan_name(self, vlan_name: str):
        self.vlan_name = vlan_name

    def set_vrf_name(self, vrf_name: str):
        self.vrf_name = vrf_name

    def set_prefix(self, prefix):
        self.prefix = prefix

    def append_dhcp_option(self, dhcp_option: DNSMasq_DHCP_Option):
        self.dhcp_options.append(dhcp_option)

    def append_dhcp_range(self, dhcp_range: DNSMasq_DHCP_Range):
        self.dhcp_ranges.append(dhcp_range)

    def append_dhcp_host(self, dhcp_host: DNSMasq_DHCP_Host):
        self.dhcp_hosts.append(dhcp_host)


    def get_header(self):
        # Example
        ### Site:    Home
        ### Role:    Untagged
        ### Vlan:    66 (Home VLAN) with ID: 66
        ### VRF:     vrf_66_homelan
        ### Prefix:  192.168.1.0/24

        res = []

        if self.scope is not None:
            res.append(f"### Site:    {self.site}")

        if self.role is not None:
            res.append(f"### Role:    {self.role['name']}")

        if self.vlan_id is not None and self.vlan_name is not None:
            res.append(f"### Vlan:    {self.vlan_name} with ID: {str(self.vlan_id)}")
        elif self.vlan_id is not None:
            res.append(f"### Vlan ID: {str(self.vlan_id)}")
        elif self.vlan_name is not None:
            res.append(f"### Vlan:    {self.vlan_name}")

        if self.vrf_name is not None:
            res.append(f"### VRF:     {self.vrf_name}")

        if self.prefix is not None:
            res.append(f"### Prefix:  {self.prefix}")

        return "\n".join(res)

    def get_options(self):
        return self.dhcp_options

    def get_ranges(self):
        return self.dhcp_ranges

    def get_hosts(self):
        return self.dhcp_hosts


class DNSMasq_DHCP_Config:
    def __init__(self):
        self.dhcp_config_generic_switches = []
        self.dhcp_config_sections = []

    def append_to_dhcp_config_generic_switches(self, obj: DNSMasq_DHCP_Generic_Switchable):
        self.dhcp_config_generic_switches.append(obj)

    def append_to_dhcp_config_sections(self, obj: DNSMasq_DHCP_Section):
        self.dhcp_config_sections.append(obj)

    def print(self):
        print(self)

    def __str__(self):
        res = []

        for sw in self.dhcp_config_generic_switches:
            res.append(str(sw))

        for sec in self.dhcp_config_sections:
            res.append(str(""))
            res.append(str(""))
            res.append(str(sec.get_header()))

            res.append(str(""))
            for opts in sec.get_options():
                res.append(str(opts))

            res.append(str(""))
            for ran in sec.get_ranges():
                res.append(str(ran))

            res.append(str(""))
            for host in sec.get_hosts():
                res.append(str(host))

        return "\n".join(res)


