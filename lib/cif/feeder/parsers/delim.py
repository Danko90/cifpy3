__author__ = 'James DeVincentis <james.d@hexhost.net>'

from ..parser import Parser


class Delim(Parser):
    def __init__(self):
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
            for x in range(1, self.parsing_details["start"]+1):
                if self.file.tell() >= self.file_size:
                    self.parsing = False
                    return
                self.file.readline()
                self.total_objects += 1

        objects = 0
        while objects < max_objects:
            if self.file.tell() >= self.file_size:
                self.parsing = False
                break

            line = self.file.readline().strip()

            match = line.split(self.parsing_details["pattern"])

            if match is None:
                continue

            if line[0].startswith('#') or line[0].startswith(';'):
                continue

            if len(match) != self.valuecount:
                if line[0].startswith('#') or line[0].startswith(';') or len(line) == 0:
                    continue
                self.logging.debug(
                    "No Match - feed: {4}; position {0}; contents: '{1}'; match-count: {3}; values: {2}".format(
                        self.file.tell(), match, len(self.parsing_details["values"]), len(match),
                        self.parsing_details['feed_name']
                    )
                )
                continue

            observable = self.create_observable_from_meta_if_not_in_journal(match)

            if observable is not None:
                observables.append(observable)
                objects += 1
                self.total_objects += 1

            if self.ending and self.total_objects >= self.end:
                self.parsing = False
                break

        self.writejournal()

        return observables
