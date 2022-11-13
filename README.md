# Netbox tools 3
With these tools you can generate configuration files based on data in Netbox.

# Important!
Some tools require special tags to be added into your Netbox and assigned to objects to work.

## What is Netbox?
"NetBox is the leading solution for modeling and documenting modern networks. By combining the traditional disciplines of IP address management (IPAM) and datacenter infrastructure management (DCIM) with powerful APIs and extensions, NetBox provides the ideal "source of truth" to power network automation.", [https://github.com/netbox-community/netbox](https://github.com/netbox-community/netbox)

## Compatibility with
The tools available here are tested with Netbox v3.3.x.

# Netbox to DNSMASQ DHCP Configuration
Using "netbox-2-dnsmasq-dhcp.py" will generate a DNSMasq compatible DHCP configuration file for its configuration service.

More information here: [README.dnsmasq.dhcp.md](README.dnsmasq.dhcp.md)

## What is DNSMasq?
"Dnsmasq provides network infrastructure for small networks: DNS, DHCP, router advertisement and network boot.", [https://thekelleys.org.uk/dnsmasq/doc.html](https://thekelleys.org.uk/dnsmasq/doc.html)

# Netbox to PowerDNS Recursor Configuration
Using "./netbox-2-powerdns-rec.py" will generate zonefile compatible with PowerDNS Recursor and Bind. The zonefile can be extended with a footer file.

It can also generate a reverse lookup file zonefile.

More information here: [README.powerdns.rec.md](README.powerdns.rec.md)

## What is PowerDNS Recursor?
"The PowerDNS Recursor is a high-end, high-performance resolving name server which powers the DNS resolution of at least a hundred million subscribers.", [https://www.powerdns.com/recursor.html](https://www.powerdns.com/recursor.html)