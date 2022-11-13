# netbox-2-powerdns-rec.py
Using "./netbox-2-powerdns-rec.py" will generate zonefile compatible with PowerDNS Recursor and Bind. The zonefile can be extended with a footer file.

It can also generate a reverse lookup file zonefile.

## PowerDNS Recursor configuration
The script will fetch all devices and its interfaces. It will concatenate each of the interfaces and generated forward and reverse zonefile files. The primary IP address will get a CNAME-ed shortened hostname to the interface name and device concatenated name.

Copy `netbox.config.example` to `netbox.config`, adjust the example data and fill the URL and auth key and check the results in the default output file location.


### Zonefile output
```
koeroo.lan. 86400 IN SOA ns.koeroo.lan. hostmaster.koeroo.lan. 7 86400 7200 3600000 1800
@ 86400 IN NS ns.koeroo.lan.
br_lan1.draytek 86400 IN A 192.168.10.1
br_net200.draytek 86400 IN A 192.168.200.1
br_net201.draytek 86400 IN A 192.168.201.1
br_net202.draytek 86400 IN A 192.168.202.1
eth0.vpn 86400 IN A 192.168.202.10
vpn 86400 IN CNAME eth0.vpn.koeroo.lan.
br_net203.draytek 86400 IN A 192.168.203.1
eth0.netbox 86400 IN A 192.168.203.11
netbox 86400 IN CNAME eth0.netbox.koeroo.lan.
eth0.syslog 86400 IN A 192.168.203.15
syslog 86400 IN CNAME eth0.syslog.koeroo.lan.
eth0.revproxy 86400 IN A 192.168.203.42
revproxy 86400 IN CNAME eth0.revproxy.koeroo.lan.
eth0.somecloud 86400 IN A 192.168.203.45
somecloud 86400 IN CNAME eth0.somecloud.koeroo.lan.
eth0.respect 86400 IN A 192.168.203.46
respect 86400 IN CNAME eth0.respect.koeroo.lan.
eth0.kat 86400 IN A 192.168.203.53
kat 86400 IN CNAME eth0.kat.koeroo.lan.
eth0.seaport 86400 IN A 192.168.203.54
seaport 86400 IN CNAME eth0.seaport.koeroo.lan.
eth0.plex 86400 IN A 192.168.203.70
plex 86400 IN CNAME eth0.plex.koeroo.lan.
eth0.mailcow 86400 IN A 192.168.203.80
mailcow 86400 IN CNAME eth0.mailcow.koeroo.lan.
eth0.homeassistant 86400 IN A 192.168.203.101
homeassistant 86400 IN CNAME eth0.homeassistant.koeroo.lan.
br_net204.draytek 86400 IN A 192.168.204.1
wlan0.esp_2b55e9 86400 IN A 192.168.204.50
esp_2b55e9 86400 IN CNAME wlan0.esp_2b55e9.koeroo.lan.
wlan0.esp_eacb50 86400 IN A 192.168.204.51
esp_eacb50 86400 IN CNAME wlan0.esp_eacb50.koeroo.lan.
wlan0.esp_eacffb 86400 IN A 192.168.204.52
esp_eacffb 86400 IN CNAME wlan0.esp_eacffb.koeroo.lan.
wlan0.esp_ea85cd 86400 IN A 192.168.204.53
```

## Usage
```
usage: netbox-2-dhcp-dns.py [-h] [-v] [-k AUTHKEY]
                           [-do DNSMASQ_DHCP_OUTPUT_FILE]
                           [-bu NETBOX_BASE_URL]
                           [-ltr DHCP_DEFAULT_LEASE_TIME_RANGE]
                           [-lth DHCP_DEFAULT_LEASE_TIME_HOST]
                           [-min DHCP_HOST_RANGE_OFFSET_MIN]
                           [-max DHCP_HOST_RANGE_OFFSET_MAX]
                           [-lf DHCP_LEASE_FILE] [-da]
                           [-ddd DHCP_DEFAULT_DOMAIN] [-z ZONEFILE]
                           [-zia ZONEFILE_IN_ADDR] [-rl] [-e ZONEHEADER]
                           [-f ZONEFOOTER]

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode. Default is off
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
  -lf DHCP_LEASE_FILE, --dhcp-lease-file DHCP_LEASE_FILE
                        DHCP Lease file.
  -da, --dhcp-authoritive
                        Set DHCP Authoritive flag
  -ddd DHCP_DEFAULT_DOMAIN, --dhcp-default-domain DHCP_DEFAULT_DOMAIN
                        DHCP Default Domain.
  -z ZONEFILE, --zonefile ZONEFILE
                        Zonefile format to be consumed by Bind or PowerDNS.
  -zia ZONEFILE_IN_ADDR, --zonefile-in-addr ZONEFILE_IN_ADDR
                        Zonefile format to be consumed by Bind or PowerDNS,
                        but specifically for the reverse lookups.
  -rl, --relativize     Create relativized names in the zonefile
  -e ZONEHEADER, --zoneheader ZONEHEADER
                        Zonefile header template.
  -f ZONEFOOTER, --zonefooter ZONEFOOTER
                        Zonefile footer template.
```

## Example script to mash it all up
```
echo "Running netbox-2-dhcp-dns.py"

~/netbox-tools/netbox-2-dhcp-dns.py \
    --authkey <heregoesyourkey> \
    --base-url http://netbox.koeroo.local \
    --dnsmasq-dhcp-output-file /tmp/generated-dhcp.conf \
    --dhcp-default-lease-time-range 600m \
    --dhcp-default-lease-time-host 90m \
    --dhcp-host-range-offset-min 100 \
    --dhcp-host-range-offset-max 199 \
    --dhcp-lease-file /var/cache/dnsmasq/dnsmasq-dhcp.leasefile \
    -da \
    --dhcp-default-domain koeroo.local \
    --zonefile /tmp/generated-zonefile \
    --zoneheader /home/pi/config/dns/zonefiles/templates/koeroo.local.header \
    --zonefooter /home/pi/config/dns/zonefiles/templates/koeroo.local.footer \
    --zonefile-in-addr /tmp/generated-168.192.in-addr.arpa.local

if [ $? -ne 0 ]; then
    echo "Error!"
    exit 1
fi

sudo cp \
    /tmp/generated-dhcp.conf \
    /etc/dnsmasq.d/dhcp.conf

echo "Reloading DNSMasq"
sudo systemctl restart dnsmasq

sudo cp \
    /tmp/generated-zonefile \
    /etc/powerdns/zonefiles/koeroo.local

echo "Backup running zonefile"
sudo cp -v /etc/powerdns/zonefiles/koeroo.local        /etc/powerdns/zonefiles/koeroo.local.backup
sudo cp -v /tmp/generated-zonefile                     /etc/powerdns/zonefiles/koeroo.local
     cp -v /tmp/generated-zonefile                     /home/pi/config/dns/powerdns/zonefiles/koeroo.local
sudo cp -v /tmp/generated-168.192.in-addr.arpa.local   /etc/powerdns/zonefiles/168.192.in-addr.arpa.local

### Assuming both koeroo.local and 168.192.in-addr.arpa.local are configured in
### recursor.conf to be loaded for the zone koeroo.local. and 168.192.in-addr.arpa.
echo sudo rec_control reload-zones
sudo rec_control reload-zones
```
