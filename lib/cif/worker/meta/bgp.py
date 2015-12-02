__author__ = 'James DeVincentis <james.d@hexhost.net>'

import ipaddress

import dns.reversename
import dns.resolver


# noinspection PyBroadException
def process(observable=None):
    """Takes an observable and adds meta to it. This meta processor adds BGP data (ASN, Peers)

    :param cif.types.Observable observable: Observable to add meta to
    :return: The augmented observable
    :rtype: cif.types.Observable
    """
    if observable is None:
        return observable

    if observable.otype not in ["ipv4", "ipv6"]:
        return observable

    if observable.otype == "ipv4":
        ip = ipaddress.IPv4Interface(observable.observable).ip
        asn_lookup = str(dns.reversename.from_address(str(ip))).replace(".in-addr.arpa.", "") + ".origin.asn.cymru.com"
        peer_lookup = str(dns.reversename.from_address(str(ip))).replace(".in-addr.arpa.", "") + ".peer.asn.cymru.com"

    else:
        ip = ipaddress.IPv6Interface(observable.observable).ip
        asn_lookup = str(dns.reversename.from_address(str(ip))).replace(".ip6.arpa.", "") + ".origin6.asn.cymru.com"
        peer_lookup = None

    if ip.is_private:
        return observable

    try:
        for record in dns.resolver.query(asn_lookup, 'TXT').response.answer:
            for item in record:
                (asn, prefix, cc, rir, date) = [x.strip() for x in str(item).strip('"').split('|')]
                try:
                    observable.asn = int(asn)
                except:
                    pass
                observable.cc = cc
                observable.rir = rir
                observable.prefix = prefix
    except:
        pass

    if observable.asn is not None:
        try:
            for record in dns.resolver.query("AS{0}.asn.cymru.com".format(observable.asn), 'TXT').response.answer:
                for item in record:
                    observable.asn_desc = [x.strip() for x in str(item).strip('"').split('|')][4]
        except:
            pass

    if peer_lookup is not None:
        peers = []
        peer = None
        try:
            for record in dns.resolver.query(peer_lookup, 'TXT').response.answer:
                for item in record:
                    tmp = [x.strip() for x in str(item).strip('"').split('|')]
                    peer = {"asn": tmp[0].split(" ")[0], "cc": tmp[2], "prefix": tmp[1], "rir": tmp[3], "date": tmp[4] if tmp[4] else None}
        except:
            pass
        try:
            for asn in dns.resolver.query("AS{0}.asn.cymru.com".format(peer["asn"]), 'TXT').response.answer:
                for asn_item in asn:
                    peer["asn_description"] = [x.strip() for x in str(asn_item).strip('"').split('|')][4]
        except:
            pass
        if peer is not None:
            peers.append(peer)
        observable.peers = peers

    return observable
