__author__ = 'James DeVincentis <james.d@hexhost.net>'

from .ipaddress import Ipaddress


class Ipv4(Ipaddress):
    def __init__(self, *args, **kwargs):
        self._mask = None
        super(Ipv4, self).__init__(self, args, **kwargs)

    @property
    def mask(self):
        return self._mask

    @mask.setter
    def mask(self, value):
        if value is not None:
            if not isinstance(value, int):
                raise TypeError("Mask must be an integer")
            if value > 32:
                raise TypeError("Mask cannot be greater than 32 bits for IPv6")
            if value < 0:
                raise TypeError("Mask cannot be less than 0 bits")
        self._mask = value