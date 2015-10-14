__author__ = 'James DeVincentis <james.d@hexhost.net>'

import ipaddress
import os
import re
import cif

hash_types = {
    'uuid': re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    'md5': re.compile(r'^[a-fA-F0-9]{32}$'),
    'sha1': re.compile(r'^[a-fA-F0-9]{40}$'),
    'sha256': re.compile(r'^[a-fA-F0-9]{64}$'),
    'sha512': re.compile(r'^[a-fA-F0-9]{128}$')
}


regex = {
    'url': re.compile('^(http|https|smtp|ftp|sftp)://(\S*\.\S*)$'),
    'url_2': re.compile(r'^([a-z0-9.-]+[a-z]{2,63}|\b(?:\d{1,3}\.){3}\d{1,3}\b)(:(\d+))?/+'),
    'fqdn': re.compile('^((xn--)?(--)?[a-zA-Z0-9-_]+(-[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,}(--p1ai)?$'),
    'email' : re.compile('^.*@.*\..*$')
}


def tlp(value):
    """Validates TLP formats, makes sure it's one of the pre-determined values

    :param value: Value to test
    :type value: str
    :return: Tested value
    :rtype: str
    """
    tmp = ['white', 'green', 'amber', 'red']
    if value not in tmp:
        raise KeyError("TLP value: {0:s} is not in the allowed types: {1:s}".format(value, str(tmp)))
    return value


def rir(value):
    """Validates RIR formats, makes sure it's one of the pre-determined values

    :param value: Value to test
    :type value: str
    :return: Tested value
    :rtype: str
    """
    if value is not None:
        value = value.lower()
        tmp = ['arin', 'apnic', 'ripencc', 'lacnic', 'afrinic', 'other']
        if value not in tmp:
            raise KeyError("RIR value: {0:s} is not in the allowed types: {1:s}".format(value, str(tmp)))
    return value


def lang(value):
    """Validates lang formatting, makes sure it's a string and two character string

    :param value: Value to test
    :type value: str
    :return: Tested value
    :rtype: str
    """
    if value is None:
        return value
    if not isinstance(value, str):
        raise TypeError("Lang must be a string")
    if len(value) != 2:
        raise TypeError("Lang must be a two character string")
    return value.upper()


def group(value):
    """Validates group parameter types, makes sure it's a list

    :param value: Value to test
    :type value: list
    :return: Tested value
    :rtype: list
    """
    if not isinstance(value, list):
        raise TypeError("Group must be a list")
    return value


def tags(value):
    """Validates tag formatting, makes sure it's a list

    :param value: Value to test
    :type value: list
    :return: Tested value
    :rtype: list
    """
    if not isinstance(value, list):
        return [value]
    return value


def confidence(value):
    """Validates confidence formatting

    :param value: Value to test
    :type value: int or float
    :return: Tested value
    :rtype: int or float
    """
    if not isinstance(value, float) and not isinstance(value, int):
        raise TypeError("Confidence must be an integer or float")
    return value


def country(value):
    """Validates country formatting, makes sure it's a string and two character string

    :param value: Value to test
    :type value: str
    :return: Tested value
    :rtype: str
    """
    if len(value) < 1:
        return value
    if not isinstance(value, str):
        raise TypeError("Country must be a string")
    if len(value) != 2:
        raise TypeError("Country must be a two character string")
    return value.upper()


def protocol(value):
    """Check or convert a protocol numeric to it's string value

    :param value: Value to test
    :type value: str or int
    :return: Tested value
    :rtype: str
    """
    tmp = {'ip': 1, 'tcp': 6, 'udp': 17}
    if value in tmp.keys():
        return tmp[value]
    elif not isinstance(value, int):
        raise TypeError("Protocol must be an integer or one of the following strings: {0:s}".format(tmp))
    else:
        return value


def is_ipv4(value):
    """Checks to see if a value is an IPv4 address

    :param str value: Value to test
    :return: True on successful parse of an IPv4 address, False on invalid IPv4 address
    :rtype: bool
    """
    try:
        ipaddress.IPv4Interface(value)
        return True
    except ipaddress.AddressValueError:
        return False


def is_ipv6(value):
    """Checks to see if a value is an IPv6 address

    :param str value: Value to test
    :return: True on successful parse of an IPv6 address, False on invalid IPv6 address
    :rtype: bool
    """
    try:
        ipaddress.IPv6Interface(value)
        return True
    except ipaddress.AddressValueError:
        return False


def is_url(value):
    """Checks to see if a value is a valid URL

    :param value: Value to test
    :type value: str
    :return: True on successful parse of a URL, False on invalid URL
    :rtype bool:
    """
    return regex['url'].match(value) is not None or regex['url_2'].match(value) is not None


def is_fqdn(value):
    """Checks to see if a value is a valid FQDN

    :param value: Value to test
    :type value: str
    :return: True on successful parse of an FQDN, False on invalid FQDN
    :rtype bool:
    """
    return regex['fqdn'].match(value) is not None


def is_email(value):
    """Checks to see if a value is a valid Email address

    :param value: Value to test
    :type value: str
    :return: True on successful parse of an Email address, False on invalid Email Address
    :rtype bool:
    """
    return regex['email'].match(value) is not None


def is_asn(value):
    """Checks to see if a value is a valid ASN number

    :param value: Value to test
    :type value: str
    :return: True on successful check of ASN number
    :rtype bool:
    """
    return (isinstance(value, int) or int(value)) and int(value) <= (2 ** 32 - 1)


def is_hash(value):
    """Checks to see if a value is a valid hash

    :param value: Value to test
    :type value: str
    :return: True on successful parse of an hash, False on invalid hash
    :rtype bool:
    """
    return hash_type(value) is not None


def is_binary(value):
    """Determines if value is a path to a binary file

    :param value:
    :return: bool
    """
    if value.startswith('/') and os.path.isfile(value):
        file = open(value, 'rb')
        filesize = file.seek(0, 2)
        file.seek(0)
        file.close()
        if filesize > cif.MAX_BIN_SIZE:
            cif.logging.error("File '{0}' exceeds max size of {1}; file size: {2}".format(
                value, cif.MAX_BIN_SIZE, filesize)
            )
            return False
        return True


def hash_type(value):
    """Determines hash type

    :param str value: hash value to check
    :return: Returns a string containing the hash type name or None if no hash type is matched
    :rtype: str or None
    """
    for htype, pattern in hash_types.items():
        if pattern.match(value) is not None:
            return htype
    return None
