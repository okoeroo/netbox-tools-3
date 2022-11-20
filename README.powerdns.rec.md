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
```

## Usage
```
usage: configuration.py [-h] [-v] 
                        [-c CONFIGFILE] 
                        [-k AUTHKEY] 
                        [-bu NETBOX_BASE_URL] 
                        [-d POWERDNS_REC_DOMAIN] 
                        [-z POWERDNS_REC_ZONEFILE] 
                        [-zia POWERDNS_REC_ZONEFILE_IN_ADDR] 
                        [-rl]
                        [-f POWERDNS_REC_ZONEFILE_FOOTER]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode. Default is off
  -c CONFIGFILE, --config CONFIGFILE
                        Configuration file.
  -k AUTHKEY, --authkey AUTHKEY
                        Netbox authentication key.
  -bu NETBOX_BASE_URL, --base-url NETBOX_BASE_URL
                        Netbox base URL.
  -d POWERDNS_REC_DOMAIN, --domain POWERDNS_REC_DOMAIN
                        Domain to be used in the configuration for forward and reverse lookup configurations.
  -z POWERDNS_REC_ZONEFILE, --zonefile POWERDNS_REC_ZONEFILE
                        Zonefile format to be consumed by Bind or PowerDNS.
  -zia POWERDNS_REC_ZONEFILE_IN_ADDR, --zonefile-in-addr POWERDNS_REC_ZONEFILE_IN_ADDR
                        Zonefile format to be consumed by Bind or PowerDNS, but specifically for the reverse lookups.
  -rl, --relativize     Create relativized names in the zonefile
  -f POWERDNS_REC_ZONEFILE_FOOTER, --zone-footer POWERDNS_REC_ZONEFILE_FOOTER
                        Zonefile footer template.
```

## Example script to mash it all up
```
echo "Start update: PowerDNS :: Zonefile and reverse zonefile"
./netbox-2-powerdns-rec.py \
    --config ~/netbox-tools-3-config/netbox.config

if [ $? -ne 0 ]; then
    echo "Error!"
    exit 1
fi

echo "Output files:"
ls -l /tmp/new_powerdns_zonefile
ls -l /tmp/new_powerdns_zonefile_in_addr

echo "Moving files"
sudo cp -v \
        /tmp/new_powerdns_zonefile \
        /etc/powerdns/zonefiles/koeroo.lan

sudo cp -v \
        /tmp/new_powerdns_zonefile_in_addr \
        /etc/powerdns/zonefiles/168.192.in-addr.arpa.lan

echo sudo rec_control reload-zones
sudo rec_control reload-zones

echo "Return code: $?"
```
