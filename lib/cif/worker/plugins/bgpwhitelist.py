__author__ = 'James DeVincentis <james.d@hexhost.net>'

import ipaddress
import datetime

import cif

def process(observable=None):
    """Takes an observable and creates new observables from data relating to the specified observable

    :param cif.types.Observable observable: Observable to source data from
    :return: A list of new observables related to the incoming one
    :rtype: cif.types.Observable
    """
    if observable is None:
        return None

    if observable.confidence < cif.CONFIDENCE_MIN:
        return None

    if "whitelist" not in observable.tags:
        return None

    if observable.otype != "ipv4":
        return None

    if observable.prefix is None:
        return None

    if ipaddress.IPv4Interface(observable.observable).ip.is_private:
        return None

    return [cif.types.Observable(
        {
            "observable": str(ipaddress.IPv4Interface(str(ipaddress.IPv4Interface(observable.observable).ip) + "/24").network),
            "prefix": observable.prefix,
            "tags": ["whitelist"],
            "protocol": observable.protocol,
            "portlist": observable.portlist,
            "tlp": observable.tlp,
            "group": observable.group,
            "provider": observable.provider,
            "confidence": observable._degrade_confidence(),
            "application": observable.application,
            "altid": observable.altid,
            "altid_tlp": observable.altid_tlp,
            "related": observable.id,
            "peers": observable.peers,
            "lasttime": observable.lasttime,
            "reportime": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
        }
    )]