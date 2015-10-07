__author__ = 'James DeVincentis <james.d@hexhost.net>'

import re

from ..parser import Parser


class Regex(Parser):

    def __init__(self):
        try:
            self.regex = re.compile(self.parsing_details["pattern"])
        except Exception as e:
            raise AttributeError("Regex is invalid: {0}".format(e))

        self.file.seek(0, 2)
        self.file_size = self.file.tell()
        self.file.seek(0)

    def parsefile(self, max_objects=1000):
        """Parse file provided by self.file`. Return `max_objects` at a time. This is repetitively called

        :param int max_objects: Number of objects to return
        :return: List of parsed observables
        :rtype: list
        """

        self.loadjournal()

        observables = []

        if self.total_objects == 0 and "start" in self.parsing_details and self.parsing_details["start"] > 0:
            for x in range(1, self.parsing_details["start"]):
                if self.file.tell() >= self.file_size:
                    self.parsing = False
                    break
                self.total_objects += 1

        objects = 0
        while objects <= max_objects:
            if self.file.tell() >= self.file_size:
                self.parsing = False
                break

            line = self.file.readline().strip()

            match = self.regex.search(line)

            if match is None:
                if not line.startswith('#') and not line.startswith(';') and not len(line) == 0:
                    self.logging.debug("No Match - position {0}; contents: '{1}'; match: {2}; values: {3}".format(
                        self.file.tell(), line, repr(match), len(self.parsing_details["values"]))
                    )
                continue

            if match.lastindex != self.valuecount:
                if not line.startswith('#') and not line.startswith(';') and not len(line) == 0:
                    self.logging.warning(
                        "No Match - position {0}; contents: '{1}'; match: {2}; match-count: {4}; values: {3}".format(
                            self.file.tell(), line, repr(match), len(self.parsing_details["values"]), match.lastindex
                        )
                    )
                continue

            results = []
            for index in range(1, match.lastindex+1):
                results.append(match.group(index))

            observable = self.create_observable_from_meta_if_not_in_journal(results)
            if observable is not None:
                observables.append(observable)
                self.total_objects += 1
                objects += 1

            if self.ending and self.total_objects >= self.end:
                self.parsing = False
                break

        self.writejournal()

        return observables
