# netbox-2-dnsmasq-dhcp.py

Using Netbox as source and creating DNSMasq DHCP configuration file.


## DNSMasq DHCP configuration
The script will fetch all configured prefixes from Netbox. Copy `netbox.config.example` to `netbox.config` and fill the URL and auth key and check the results in the default output file location.


### General DHCP settings
The dhcp lease file will be set on top of the output file. Optionally the dhcp-authoritative directive is set. The dhcp default domain can be set.


### Per prefix settings
From the prefixes, the associated VRF is retrieved and at which Site it is operating. Also the VLAN on which it is used is retrieved.

The name of the VRF and the name of the vlan will be concattenated and result into the name of the DHCP scope. The default gateway and DNS server is configured. The prefix will be configured with a DHCP range based on the `--dhcp-host-range-offset-min` and `--dhcp-host-range-offset-max` parameters, with a default lease time from the `--dhcp-default-lease-time-range` parameters.

#### Default gateway selection
Based on the VRF assessed, the first IP address with the tag `net_default_gateway` will be selected as the default gateway. Unless, overridden in a matching `[prefix:<cidr>]` section from the configuration file with a `gateway = <ip addr>`.

#### DNS server selection
The IP address of the default gateway will retrieved. The DNS server field associated to the IP address is retrieved and used as the DNS server. Unless, overridden in a matching `[prefix:<cidr>]` section from the configuration file with a `dns = <ip addr>`.


### DHCP example output

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

## Usage
```
usage: configuration.py [-h] [-v] [-c CONFIGFILE] [-k AUTHKEY] [-do DNSMASQ_DHCP_OUTPUT_FILE] [-bu NETBOX_BASE_URL] [-ltr DHCP_DEFAULT_LEASE_TIME_RANGE] [-lth DHCP_DEFAULT_LEASE_TIME_HOST]
                        [-min DHCP_HOST_RANGE_OFFSET_MIN] [-max DHCP_HOST_RANGE_OFFSET_MAX] [-dn DHCP_DEFAULT_NTP_SERVER] [-lf DHCP_LEASE_FILE] [-da] [-ddd DHCP_DEFAULT_DOMAIN] [-dbf DHCP_BOOT_FILENAME]
                        [-dbs DHCP_BOOT_SERVERNAME] [-dba DHCP_BOOT_ADDRESS] [-ods OVERRIDE_DNS_SERVER]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode. Default is off
  -c CONFIGFILE, --config CONFIGFILE
                        Configuration file.
  -k AUTHKEY, --authkey AUTHKEY
                        Netbox authentication key.
  -do DNSMASQ_DHCP_OUTPUT_FILE, --dnsmasq-dhcp-output-file DNSMASQ_DHCP_OUTPUT_FILE
                        DNSMasq format DHCP output file based on Netbox info.
  -bu NETBOX_BASE_URL, --base-url NETBOX_BASE_URL
                        Netbox base URL.
  -ltr DHCP_DEFAULT_LEASE_TIME_RANGE, --dhcp-default-lease-time-range DHCP_DEFAULT_LEASE_TIME_RANGE
                        DHCP Default Lease Time for a DHCP range.
  -lth DHCP_DEFAULT_LEASE_TIME_HOST, --dhcp-default-lease-time-host DHCP_DEFAULT_LEASE_TIME_HOST
                        DHCP Default Lease Time for a fixed DCHP host.
  -min DHCP_HOST_RANGE_OFFSET_MIN, --dhcp-host-range-offset-min DHCP_HOST_RANGE_OFFSET_MIN
                        DHCP Host range offset minimum.
  -max DHCP_HOST_RANGE_OFFSET_MAX, --dhcp-host-range-offset-max DHCP_HOST_RANGE_OFFSET_MAX
                        DHCP Host range offset maximum.
  -dn DHCP_DEFAULT_NTP_SERVER, --dhcp-default-ntp-server DHCP_DEFAULT_NTP_SERVER
                        Default NTP server distribute via DHCP.
  -lf DHCP_LEASE_FILE, --dhcp-lease-file DHCP_LEASE_FILE
                        DHCP Lease file.
  -da, --dhcp-authoritive
                        Set DHCP Authoritive flag
  -ddd DHCP_DEFAULT_DOMAIN, --dhcp-default-domain DHCP_DEFAULT_DOMAIN
                        DHCP Default Domain.
  -dbf DHCP_BOOT_FILENAME, --dhcp-boot-filename DHCP_BOOT_FILENAME
                        DHCP PXE boot filename.
  -dbs DHCP_BOOT_SERVERNAME, --dhcp-boot-servername DHCP_BOOT_SERVERNAME
                        DHCP PXE boot servername.
  -dba DHCP_BOOT_ADDRESS, --dhcp-boot-address DHCP_BOOT_ADDRESS
                        DHCP PXE boot address.
  -ods OVERRIDE_DNS_SERVER, --override-dns-server OVERRIDE_DNS_SERVER
                        Override DNS Server configuration with provided IP address
```

## Example netbox.config file
```
[generic]
verbose = true
netbox_base_url = http://host.lan:port
authkey = verylongkeyfromnetbox 

[dnsmasq]

[dnsmasq_dhcp]
output_file = /tmp/dhcp_new.conf
lease_file = /var/cache/dnsmasq/dnsmasq-dhcp.leasefile
authoritive = true

default_lease_time_range = 600m
default_lease_time_host = 90m
host_range_offset_min = 129
host_range_offset_max = 190

default_domain = koeroo.lan
default_ntp_server = 192.168.1.2

boot_filename = netboot.xyz.kpxe
boot_servername = netboot.xyz
boot_address = 192.168.123.45

override_dns_server = 192.168.1.3

[prefix:192.168.200.0/24]
gateway = 192.168.200.55
dns = 192.168.200.66
ntp = 192.168.200.77
```

## Example script to mash it all up
```
echo "Running ./netbox-2-dnsmasq-dhcp.py"
echo "Assuming all configuration info is in netbox.config and readable for the script."

~/netbox-tools-3/netbox-2-dnsmasq-dhcp.py
# Netbox to DNSMasq DHCP config

sudo cp \
    /tmp/dhcp_new.conf \
    /etc/dnsmasq.d/dhcp.conf

echo "Reloading DNSMasq"
sudo systemctl restart dnsmasq
```
