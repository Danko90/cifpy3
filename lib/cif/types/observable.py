__author__ = 'James DeVincentis <james.d@hexhost.net>'

import datetime
import math
import re

import dateutil.parser

import cif
from .base import Base


class Observable(Base):
    def __init__(self, *initial_data, **kwargs):
        Base.__init__(self)

        self._lang = None
        self._id = self._generate_random_hash(32)
        self._group = ['everyone']
        self._tlp = 'amber'
        self._confidence = cif.CONFIDENCE_DEFAULT
        self._tags = []
        self._description = None
        self._data = None
        self._observable = None
        self._otype = None
        self._application = None
        self._provider = None
        self._reporttime = None
        self._firsttime = None
        self._lasttime = None
        self._adata = None
        self._related = None
        self._altid = None
        self._altid_tlp = 'amber'
        self._additional_data = None
        self._call_super = True
        self._timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
        self._validation = True

        if "validation" in kwargs:
            self._validation = kwargs['validation']

        # Handle populating attributes from a call to __init__, set otype first
        for dictionary in initial_data:
            if "otype" in dictionary:
                setattr(self, "otype", dictionary["otype"])

            for key in dictionary:
                if key == "otype":
                    continue
                setattr(self, key, dictionary[key])

    def _degrade_confidence(self, c=None):
        """Degrades observable confidence. Used by workers when creating new observables based on others

        :param c: Confidence level to base off of. If specified will be used instead of self.confidence
        :type c: float or int
        :return: Degraded confidence level
        :rtype: float
        """
        if c is not None:
            return round((math.log(c) / math.log(500)) * c, 3)

        return round((math.log(self.confidence) / math.log(500)) * self.confidence, 3)

    @property
    def altid(self):
        return self._altid

    @altid.setter
    def altid(self, value):
        self._altid = value

    @property
    def altid_tlp(self):
        return self._altid_tlp

    @altid_tlp.setter
    def altid_tlp(self, value):
        self._altid_tlp = value

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        if value is not None and self._validation:
            try:
                value = datetime.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%dT%H:%I:%SZ")
            except:
                value = dateutil.parser.parse(value).strftime("%Y-%m-%dT%H:%I:%SZ")
        self._timestamp = value

    @property
    def lang(self):
        return self._lang

    @lang.setter
    def lang(self, value):
        if value is not None and self._validation:
            value = cif.types.lang(value)
        self._lang = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, value):
        if self._validation and isinstance(value, str) :
            value = value.lower()
        self._provider = value

    @property
    def group(self):
        return self._group

    @group.setter
    def group(self, value):
        if self._validation and value is not None:
            if not isinstance(value, list):
                if isinstance(value, str):
                    value = [value]
                else:
                    raise TypeError("Group must be a list")
        self._group = value

    @property
    def tlp(self):
        return self._tlp

    @tlp.setter
    def tlp(self, value):
        if self._validation:
            value = cif.types.tlp(value)
        self._tlp = value

    @property
    def confidence(self):
        return self._confidence

    @confidence.setter
    def confidence(self, value):
        if self._validation:
            value = cif.types.confidence(value)
        self._confidence = value

    @property
    def tags(self):
        return list(self._tags)

    @tags.setter
    def tags(self, value):
        if self._validation:
            value = cif.types.tags(value)
        self._tags = list(set(value))

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def application(self):
        return self._application

    @application.setter
    def application(self, value):
        self._application = value

    @property
    def adata(self):
        return self._adata

    @adata.setter
    def adata(self, value):
        self._adata = value

    @property
    def observable(self):
        return self._observable

    @observable.setter
    def observable(self, value):
        if self._validation:
            if isinstance(value, str):
                value = value.lower()
            if self.otype is None:
                if cif.types.is_ipv4(value):
                    self.otype = 'ipv4'
                elif cif.types.is_fqdn(value):
                    self.otype = 'fqdn'
                elif cif.types.is_url(value):
                    self.otype = 'url'
                elif cif.types.is_email(value):
                    self.otype = 'email'
                elif cif.types.is_hash(value):
                    self.otype = 'hash'
                elif cif.types.is_ipv6(value):
                    self.otype = 'ipv6'
                elif cif.types.is_binary(value):
                    self.otype = 'binary'
        self._observable = value

    @property
    def otype(self):
        return self._otype

    # Note: changes to otype will result in the class self mutating into a observable class
    @otype.setter
    def otype(self, value):
        if value is not None:
            if value != self._otype:
                # Try to import the module and mutate
                try:
                    module = __import__('cif.types.observables.{0:s}'.format(value.lower()), fromlist=[value.title()])
                    self.__class__ = getattr(module, value.title())
                    self._call_super = False
                    self.__init__()
                # If we can't mutate, just stay the way we are and move on.
                # We may not have distinct classes for all otypes
                except ImportError:
                    pass
        else:
            if self._validation and self.observable is not None:
                # noinspection PyTypeChecker
                if cif.types.is_ipv4(self.observable):
                    self.otype = 'ipv4'
                elif cif.types.is_fqdn(self.observable):
                    self.otype = 'fqdn'
                elif cif.types.is_url(self.observable):
                    self.otype = 'url'
                elif cif.types.is_email(self.observable):
                    self.otype = 'email'
                elif cif.types.is_hash(self.observable):
                    self.otype = 'hash'
                elif cif.types.is_ipv6(self.observable):
                    self.otype = 'ipv6'
                elif cif.types.is_binary(self.observable):
                    self.otype = 'binary'
                pass
        if value is not None:
            self._otype = value.lower()

    @property
    def reporttime(self):
        return self._reporttime

    @reporttime.setter
    def reporttime(self, value):
        if self._validation and value is not None:
            try:
                value = datetime.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%dT%H:%I:%SZ")
            except:
                value = dateutil.parser.parse(value).strftime("%Y-%m-%dT%H:%I:%SZ")
        self._reporttime = value

    @property
    def firsttime(self):
        return self._firsttime

    @firsttime.setter
    def firsttime(self, value):
        if self._validation and value is not None:
            try:
                value = datetime.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%dT%H:%I:%SZ")
            except:
                value = dateutil.parser.parse(value).strftime("%Y-%m-%dT%H:%I:%SZ")
        self._firsttime = value

    @property
    def lasttime(self):
        return self._lasttime

    @lasttime.setter
    def lasttime(self, value):
        if self._validation and value is not None:
            try:
                value = datetime.datetime.fromtimestamp(int(value)).strftime("%Y-%m-%dT%H:%I:%SZ")
            except:
                value = dateutil.parser.parse(value).strftime("%Y-%m-%dT%H:%I:%SZ")
        self._lasttime = value
