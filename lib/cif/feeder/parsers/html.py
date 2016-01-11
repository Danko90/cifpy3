__author__ = 'James DeVincentis <james.d@hexhost.net>'

from ..parser import Parser
from bs4 import BeautifulSoup

class Html(Parser):
    def __init__(self):
        self.html = BeautifulSoup(self.file.read())
        self.table = self.html.find("table", attrs={"id":self.parsing_details['node']})
        self.headings = [th.get_text().strip() for th in self.table.find("tr").find_all("th")]
        self.entries = []
        for row in self.table.find_all("tr")[1:]:
            self.entries.append(dict(zip(self.headings, (td.get_text().strip() for td in row.find_all("td")))))
        self.entries_count = len(self.entries)
        self.position = 0

    def parsefile(self, max_objects=1000):
        """Parse file provided by self.file`. Return `max_objects` at a time. This is repetitively called

        :param int max_objects: Number of objects to return
        :return: List of parsed observables
        :rtype: list
        """

        self.loadjournal()

        observables = []

        if self.total_objects == 0 and "start" in self.parsing_details and self.parsing_details["start"] > 1:
            self.position = self.parsing_details["start"]

        objects = 0
        while objects <= max_objects:

            if self.position >= self.entries_count:
                self.parsing = False
                break
            entry = self.entries[self.position]
            self.position += 1
            observable = self.create_observable_from_meta_if_not_in_journal(entry, usemap=True)
            if observable is not None:
                observables.append(observable)
                objects += 1
            self.total_objects += 1

            if self.ending and self.total_objects >= self.end:
                self.parsing = False
                break

        self.writejournal()

        return observables
