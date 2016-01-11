__author__ = 'James DeVincentis <james.d@hexhost.net>'

import copy
import pickle
import os
import re
import cif


class Parser(object):
    def __init__(self, **kwargs):
        self.basemeta = kwargs["basemeta"]
        self.parsing_details = kwargs["parsing_details"]
        self.parsing = True
        self.journal = None
        self.new_journal = None
        self.total_objects = 0
        self.file = kwargs["file"]
        self.logging = cif.logging.getLogger('Parser')
        self.valuecount = len(self.parsing_details["values"])
        self.end = 0
        if "end" in self.parsing_details and self.parsing_details["end"] > 0:
            self.end = self.parsing_details["end"]
        self.ending = (self.end > 0)
        try:
            module = __import__('cif.feeder.parsers.{0:s}'.format(self.parsing_details["parser"].lower()),
                                fromlist=[self.parsing_details["parser"].title()])
            self.__class__ = getattr(module, self.parsing_details["parser"].title())
            self.__init__()
        except Exception as e:
            self.logging.fatal("No parser named '{0}' for feed '{1}': {2}".format(
                self.parsing_details["parser"].title(), self.parsing_details['remote'], e)
            )
            raise Exception("No parser named '{0}'".format(self.parsing_details["parser"].title()))

    def parsefile(self, *args, **kwargs):
        raise Exception("a call to parseFile must be overloaded in the parser to be used.")

    def writejournal(self):
        self.logging.debug("Writing Journal to '{0}'".format(self.parsing_details["journal"]))
        pickle.dump(self.new_journal, open(self.parsing_details["journal"], 'wb'))

    def loadjournal(self):
        if self.journal is None:
            self.logging.debug("Loading Journal from '{0}'".format(self.parsing_details['journal']))
            self.journal = {}
            self.new_journal = {}
            if os.path.exists(self.parsing_details["journal"]):
                self.journal = pickle.load(open(self.parsing_details["journal"], 'rb'))

    def assign_meta_using_map(self, line):
        meta = {}
        for index, metakey in enumerate(self.parsing_details["values"]):
            try:
                if metakey is None:
                    continue
                meta[metakey] = line[self.parsing_details["map"][index]]
            except Exception as e:
                raise Exception("Parsing error. Not enough groups to satisfy values: {0}".format(e))
        return meta

    def assignmeta(self, line):
        meta = {}
        # Loop through the metakeys for the match
        for index, metakey in enumerate(self.parsing_details["values"]):
            # Get the metakey and set the dictionary from the regex match
            # Regex operates in an off by one (since 0 is the entire match), so add one
            try:
                # Ignore fields with a null metakey
                if metakey is None:
                    continue
                # Assign the meta
                meta[metakey] = line[index]

            # Catch the exceptions so we don't bail out
            except Exception as e:
                raise RuntimeError("Not enough meta to fill values: values: {0}; meta: {1}".format(
                    self.parsing_details['values'], line)
                ) from e
        return meta

    def checkjournal(self, observable):
        return observable not in self.journal

    def create_observable_from_meta(self, meta):
        tmp = copy.deepcopy(self.basemeta)
        tmp.update(copy.deepcopy(meta))

        for key, value in tmp.items():
            if isinstance(value, str):
                match = re.finditer('(?:<([^<>.]+)>)', value)
                if match is not None:
                    for m in match:
                        if m.group(1) in tmp:
                            tmp[key] = value.replace(m.group(0), tmp[m.group(1)])

        return cif.types.Observable(tmp)

    def create_observable_from_meta_if_not_in_journal(self, line, usemap=False):
        observable = None

        if usemap:
            meta = self.assign_meta_using_map(line)
        else:
            meta = self.assignmeta(line)

        if self.checkjournal(meta["observable"]):
            try:
                observable = self.create_observable_from_meta(meta)
            except Exception as e:
                self.logging.exception("Could not create observable from meta: {0}: {1}".format(meta, e))
                return None
            self.new_journal[meta['observable']] = observable.id
        else:
            self.new_journal[meta['observable']] = self.journal[meta['observable']]

        return observable
    
    def cleanup(self):
        pass
