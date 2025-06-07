from ipaddress import IPv4Network, IPv6Network, ip_network


class Netbox_Prefix:
    def __init__(self, data: dict):
        self.data: dict = data
        self.prefix: IPv4Network | IPv6Network = ip_network(self.data['prefix'], strict=True)

    def __repr__(self) -> str:
        return str(self.prefix)
    
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


def filter_processing_of_prefix(ctx: dict, prefix_obj: Netbox_Prefix) -> bool:
    """_summary_
        This is a filter to apply to a prefix to see if it must be filtered.

    Args:
        ctx (dict): _description_
        prefix_obj (Netbox_Prefix): _description_

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


