# Netbox tools 3
With these tools you can generate configuration files based on data in Netbox. It's capable of generating DNSMasq DCHP configuration compatible config file which can be dropped in `/etc/dnsmasq.d/`. It will also be able to generate a bind-compatible zonefile for both forward and reverse lookups. This is tested in combination with the PowerDNS Recursor.

# Important!
Special tags are required for the tooling to work properly. Learn more in the tags section, or go for the direct approach with the *quick install*.

# Quick install
1. Ensure you have prefixes, devices, virtual machines and IP addresses in your Netbox configured. Also, apply IP ranges.
2. Add the tag `net_default_gateway` to the default gateway IP-address, when that IP is associated to a device and has the default gateway role of a subnet.
3. For IP ranges to be included, add the tag `net_dhcp_range` to the IP range which should be included.
4. On the prefixes that must be included in the configuration, add the tag `dnsmasq_generator` to each prefix.
5. Optionally, assign vlans and associated prefixes to each.
6. Setup and configure the tooling as follows:

```
cd /tmp
git clone https://github.com/okoeroo/netbox-tools-3.git
cd netbox-tools-3
./scripts/create-venv.sh
source ./scripts/activate-venv.sh

cp netbox.config.example netbox.config

echo "Adjust netbox.config"
python3 netbox-2-dnsmasq-dhcp-and-powerdns-rec.py -c netbox.config

```

# Associated tools

## What is Netbox?
"NetBox is the leading solution for modeling and documenting modern networks. By combining the traditional disciplines of IP address management (IPAM) and datacenter infrastructure management (DCIM) with powerful APIs and extensions, NetBox provides the ideal "source of truth" to power network automation.", [https://github.com/netbox-community/netbox](https://github.com/netbox-community/netbox)

### Compatibility
The tools available here are tested with the lastest Netbox versions.

## What is DNSMasq?
"Dnsmasq provides network infrastructure for small networks: DNS, DHCP, router advertisement and network boot.", [https://thekelleys.org.uk/dnsmasq/doc.html](https://thekelleys.org.uk/dnsmasq/doc.html)

## What is PowerDNS Recursor?
"The PowerDNS Recursor is a high-end, high-performance resolving name server which powers the DNS resolution of at least a hundred million subscribers.", [https://www.powerdns.com/recursor.html](https://www.powerdns.com/recursor.html)



# Netbox to DNSMASQ DHCP Configuration
Using "netbox-2-dnsmasq-dhcp.py" will generate a DNSMasq compatible DHCP configuration file for its configuration service.

Using Netbox as source and creating DNSMasq DHCP configuration file.


## DNSMasq DHCP configuration
The script will fetch all configured prefixes from Netbox. Copy `netbox.config.example` to `netbox.config` and fill the URL and auth key and check the results in the default output file location.


### General DHCP settings
The dhcp lease file will be set on top of the output file. Optionally the dhcp-authoritative directive is set. The dhcp default domain can be set.


### Per prefix settings
From the prefixes, the associated prefix is retrieved and at which Site it is operating. Also the VLAN on which it is used is retrieved.

The name of the prefix and the name of the vlan will be concattenated and result into the name of the DHCP scope. The default gateway and DNS server is configured. The prefix will be configured with a DHCP range based on the `--dhcp-host-range-offset-min` and `--dhcp-host-range-offset-max` parameters, with a default lease time from the `--dhcp-default-lease-time-range` parameters.

#### Default gateway selection
Based on the prefix assessed, the first IP address with the tag `net_default_gateway` will be selected as the default gateway. Unless, overridden in a matching `[prefix:<cidr>]` section from the configuration file with a `gateway = <ip addr>`.

#### DNS server selection
The IP address of the default gateway will retrieved. The DNS server field associated to the IP address is retrieved and used as the DNS server. Unless, overridden in a matching `[prefix:<cidr>]` section from the configuration file with a `dns = <ip addr>`.




# Netbox to PowerDNS Recursor Configuration
The script will fetch all devices and its interfaces. It will concatenate each of the interfaces and generated forward and reverse zonefile files. The primary IP address will get a CNAME-ed shortened hostname to the interface name and device concatenated name.

The resulting zonefiles for forward and reverse lookups will be generated in separate files.


# Configuration file example
```
[generic]
verbose = true
netbox_base_url = http://netbox.koeroo.lan:8514
authkey = myauthkeyonnetbox


[powerdns_rec]
zonefile = /Users/oscarprive/dvl/netbox-tools-3/output/new_powerdns_zonefile
zonefile_in_addr = /Users/oscarprive/dvl/netbox-tools-3/output/new_powerdns_zonefile_in_addr
domain = koeroo.lan
zonefile_footer = /Users/oscarprive/dvl/netbox-tools-3/testing/zonefile.footer


[dnsmasq_dhcp]
output_file = /Users/oscarprive/dvl/netbox-tools-3/output/new_dnsmasq_dhcp.conf
lease_file = /var/cache/dnsmasq/dnsmasq-dhcp.leasefile
authoritive = true

default_lease_time_range = 600m
default_lease_time_host = 90m
host_range_offset_min = 129
host_range_offset_max = 190

default_domain = koeroo.lan
domain_search = koeroo.lan
default_ntp_server = 192.168.1.2

# override_dns_server = 192.168.1.2

boot_filename = netboot.xyz.kpxe
boot_servername = netboot.xyz
boot_address = 192.168.203.47

prefix_in_scope_by_tag = dnsmasq_generator
default_gateway_per_prefix_identified_by_tag = net_default_gateway


# Main flat network - vlan 66
[prefix:192.168.1.0/24]
gateway = 192.168.1.1
dns = 192.168.1.2
ntp = 192.168.1.2

# Maintenance - vlan 10
[prefix:192.168.10.0/24]
gateway = 192.168.10.1
dns = 192.168.10.2
ntp = 192.168.10.2

# Guest network - vlan 200
[prefix:192.168.200.0/24]
gateway = 192.168.200.1
dns = 9.9.9.9
ntp = 178.239.19.59

# Storage network - vlan 201
[prefix:192.168.201.0/24]
gateway = 192.168.201.1
dns = 192.168.201.2
ntp = 192.168.201.2

# VPN network - vlan 202
[prefix:192.168.202.0/24]
gateway = 192.168.202.1
dns = 192.168.202.2
ntp = 192.168.202.2

# Virtual machines - vlan 203
[prefix:192.168.203.0/24]
gateway = 192.168.203.1
dns = 192.168.203.2
ntp = 192.168.203.2

# IoT network - vlan 204
[prefix:192.168.204.0/24]
gateway = 192.168.204.1
dns = 192.168.204.2
ntp = 192.168.204.2
```

# Output examples

## DHCP example output

```
dhcp-leasefile=/var/cache/dnsmasq/dnsmasq-dhcp.leasefile
dhcp-authoritative
domain=koeroo.local

### Site:    Home
### Role:    Untagged
### Vlan:    Home VLAN (66) with ID: 66
### VRF:     vrf_66_homelan
### Prefix:  192.168.1.0/24

dhcp-option=vrf_66_homelan_vlan_66,3,192.168.1.254  # Default Gateway
dhcp-option=vrf_66_homelan_vlan_66,6,192.168.1.1  # Default DNS
dhcp-range=vrf_66_homelan_vlan_66,192.168.1.100,192.168.1.199,255.255.255.0,600m

dhcp-host=vrf_66_homelan_vlan_66,B8:27:EB:FF:FF:FF,kpnpibox_eth0,192.168.1.1,90m
dhcp-host=vrf_66_homelan_vlan_66,52:54:00:FF:FF:FF,unifi_eth0,192.168.1.3,90m
dhcp-host=vrf_66_homelan_vlan_66,80:EE:73:FF:FF:FF,mainport_mainbridge,192.168.1.4,90m
```

## Zonefile for forward lookups
```
koeroo.lan. 86400 IN SOA ns.koeroo.lan. hostmaster.koeroo.lan. 7 86400 7200 3600000 1800
@ 86400 IN NS ns.koeroo.lan.
vlan10.rocket 86400 IN A 192.168.10.1
vlan200.rocket 86400 IN A 192.168.200.1
eth0_200.hotpie 86400 IN A 192.168.200.2
vlan201.rocket 86400 IN A 192.168.201.1
eth0_201.hotpie 86400 IN A 192.168.201.2
lan2.deadpool 86400 IN A 192.168.201.11
vlan202.rocket 86400 IN A 192.168.202.1
eth0_202.hotpie 86400 IN A 192.168.202.2
ge_8.hp_3com_switch 86400 IN A 192.168.202.10
```

## Zonefile for reverse lookups
```
168.192.in-addr.arpa. 86400 IN SOA ns.koeroo.lan. hostmaster.koeroo.lan. 7 86400 7200 3600000 1800
@ 86400 IN NS ns.koeroo.lan.
200.0.8.10.in-addr.arpa. 86400 IN PTR tun0.remote_koeroo_net.koeroo.lan.
1.1.168.192.in-addr.arpa. 86400 IN PTR bridge.rocket.koeroo.lan.
2.1.168.192.in-addr.arpa. 86400 IN PTR eth0.hotpie.koeroo.lan.
3.1.168.192.in-addr.arpa. 86400 IN PTR eth0_1.hotpie.koeroo.lan.
4.1.168.192.in-addr.arpa. 86400 IN PTR mainbridge.mainport.koeroo.lan.
5.1.168.192.in-addr.arpa. 86400 IN PTR eth0.nickfury.koeroo.lan.
6.1.168.192.in-addr.arpa. 86400 IN PTR reserved_ip_address.
```

## Usage
```
usage: netbox-2-dnsmasq-dhcp-and-powerdns-rec.py 
                        [-h] [-v] 
                        [-c CONFIGFILE] 
                        [-k AUTHKEY] 
                        [-bu NETBOX_BASE_URL] 
                        [-do DNSMASQ_DHCP_OUTPUT_FILE] 
                        [-ltr DHCP_DEFAULT_LEASE_TIME_RANGE]
                        [-lth DHCP_DEFAULT_LEASE_TIME_HOST] 
                        [-min DHCP_HOST_RANGE_OFFSET_MIN] 
                        [-max DHCP_HOST_RANGE_OFFSET_MAX] 
                        [-dn DHCP_DEFAULT_NTP_SERVER]
                        [-lf DHCP_LEASE_FILE] 
                        [-da] 
                        [-ddd DHCP_DEFAULT_DOMAIN] 
                        [-dds DHCP_DOMAIN_SEARCH] 
                        [-dbf DHCP_BOOT_FILENAME] 
                        [-dbs DHCP_BOOT_SERVERNAME]
                        [-dba DHCP_BOOT_ADDRESS] 
                        [-ods OVERRIDE_DNS_SERVER] 
                        [-pit PREFIX_IN_SCOPE_BY_TAG] 
                        [-dgpt DEFAULT_GATEWAY_PER_PREFIX_IDENTIFIED_BY_TAG]
                        [-srpt SELECTED_RANGE_IN_PREFIX_BY_TAG] 
                        [-d POWERDNS_REC_DOMAIN] 
                        [-z POWERDNS_REC_ZONEFILE] 
                        [-zia POWERDNS_REC_ZONEFILE_IN_ADDR] 
                        [-rl]
                        [-f POWERDNS_REC_ZONEFILE_FOOTER]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode. Default is off
  -c, --config CONFIGFILE
                        Configuration file.
  -k, --authkey AUTHKEY
                        Netbox authentication key.
  -do, --dnsmasq-dhcp-output-file DNSMASQ_DHCP_OUTPUT_FILE
                        DNSMasq format DHCP output file based on Netbox info.
  -bu, --base-url NETBOX_BASE_URL
                        Netbox base URL.
  -ltr, --dhcp-default-lease-time-range DHCP_DEFAULT_LEASE_TIME_RANGE
                        DHCP Default Lease Time for a DHCP range.
  -lth, --dhcp-default-lease-time-host DHCP_DEFAULT_LEASE_TIME_HOST
                        DHCP Default Lease Time for a fixed DCHP host.
  -min, --dhcp-host-range-offset-min DHCP_HOST_RANGE_OFFSET_MIN
                        DHCP Host range offset minimum.
  -max, --dhcp-host-range-offset-max DHCP_HOST_RANGE_OFFSET_MAX
                        DHCP Host range offset maximum.
  -dn, --dhcp-default-ntp-server DHCP_DEFAULT_NTP_SERVER
                        Default NTP server distribute via DHCP.
  -lf, --dhcp-lease-file DHCP_LEASE_FILE
                        DHCP Lease file.
  -da, --dhcp-authoritive
                        Set DHCP Authoritive flag
  -ddd, --dhcp-default-domain DHCP_DEFAULT_DOMAIN
                        DHCP Default Domain.
  -dds, --dhcp-domain-search DHCP_DOMAIN_SEARCH
                        DHCP Domain Search.
  -dbf, --dhcp-boot-filename DHCP_BOOT_FILENAME
                        DHCP PXE boot filename.
  -dbs, --dhcp-boot-servername DHCP_BOOT_SERVERNAME
                        DHCP PXE boot servername.
  -dba, --dhcp-boot-address DHCP_BOOT_ADDRESS
                        DHCP PXE boot address.
  -ods, --override-dns-server OVERRIDE_DNS_SERVER
                        Override DNS Server configuration with provided IP address
  -pit, --prefix-in-scope-by-tag PREFIX_IN_SCOPE_BY_TAG
                        Add all prefixes, unless scoped by finding this set tag name to a prefix
  -dgpt, --default-gateway-per-prefix-identified-by-tag DEFAULT_GATEWAY_PER_PREFIX_IDENTIFIED_BY_TAG
                        Selector of the default gateway per prefix. The IP address of the 
                        default gateway is identified by the configured tag name. Recommended is
                        to use 'net_default_gateway'
  -srpt, --selected-range-in-prefix-by-tag SELECTED_RANGE_IN_PREFIX_BY_TAG
                        Selector range in prefix by tag.
  -d, --domain POWERDNS_REC_DOMAIN
                        Domain to be used in the configuration for forward and reverse 
                        lookup configurations.
  -z, --zonefile POWERDNS_REC_ZONEFILE
                        Zonefile format to be consumed by Bind or PowerDNS.
  -zia, --zonefile-in-addr POWERDNS_REC_ZONEFILE_IN_ADDR
                        Zonefile format to be consumed by Bind or PowerDNS, but 
                        specifically for the reverse lookups.
  -rl, --relativize     Create relativized names in the zonefile
  -f, --zone-footer POWERDNS_REC_ZONEFILE_FOOTER
                        Zonefile footer template.
```

