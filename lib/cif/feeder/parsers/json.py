__author__ = 'James DeVincentis <james.d@hexhost.net>'

import json

from ..parser import Parser


class Json(Parser):
    def __init__(self):

        # Try and parse the JSON data, this is one instance where we have to load it all
        raw = self.file.read()
        if raw.startswith('{') and raw.endswith('}'):
            raw = "[{0}]".format(raw)
        self.json_data = json.loads(raw)
        self.json_iter = iter(self.json_data)

    def parsefile(self, max_objects=1000):
        """Parse file provided by self.file`. Return `max_objects` at a time. This is repetitively called

        :param int max_objects: Number of objects to return
        :return: List of parsed observables
        :rtype: list
        """

        self.loadjournal()

        observables = []

        if self.total_objects == 0 and "start" in self.parsing_details and self.parsing_details["start"] > 1:
            for x in range(1, self.parsing_details["start"]):
                try:
                    line = next(self.json_iter)
                    if line is None:
                        self.parsing = False
                        break
                    self.total_objects += 1
                except StopIteration:
                    self.parsing = False
                    break

        objects = 0
        while objects < max_objects:
            try:
                line = next(self.json_iter)
                if line is None:
                    self.parsing = False
                    break
            except StopIteration:
                self.parsing = False
                break

            observable = self.create_observable_from_meta_if_not_in_journal(line, usemap=True)
            if observable is not None:
                observables.append(observable)
                objects += 1
            self.total_objects += 1

            if self.ending and self.total_objects >= self.end:
                self.parsing = False
                break

        self.writejournal()

        return observables
