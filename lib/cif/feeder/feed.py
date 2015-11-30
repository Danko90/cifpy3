__author__ = 'James DeVincentis <james.d@hexhost.net>'

import os
import datetime
import gzip
import tempfile
import zipfile
import copy

import yaml
import requests

import cif
from .parser import Parser
from ..worker import tasks
from pprint import pprint

class Feed(object):
    def __init__(self, feed_file):
        self.feed_file = feed_file
        self.feed_config = {}
        self.parser = None
        self.logging = cif.logging.getLogger('FEED')

        try:
            self.logging.debug("Opening Feed file for parsing : {0}".format(self.feed_file))
            with open(self.feed_file, 'r') as stream:
                self.logging.debug("Parsing feed file")
                feed_config = yaml.load(stream)
        except IOError as e:
            self.logging.exception("Could not parse feed file {0}: {1}".format(self.feed_file), e)
            return

        if "feeds" not in feed_config.keys():
            self.logging.info("No feeds configured inside of {0}. Moving on to next file.".format(self.feed_file))
            return

        if "parser" in feed_config.keys():
            for key, value in feed_config["feeds"].items():
                if "parser" not in feed_config["feeds"][key].keys():
                    feed_config["feeds"][key]["parser"] = feed_config["parser"]

        if "defaults" in feed_config.keys():
            for key, value in feed_config["defaults"].items():
                for k, v in feed_config["feeds"].items():
                    if key not in feed_config["feeds"][k].keys():
                        feed_config["feeds"][k][key] = value

        self.feed_config = feed_config

    def processall(self):
        if "feeds" not in self.feed_config.keys():
            return
        for feed_name, feed in self.feed_config["feeds"].items():
            self.process(self, feed_name)
            
    def process(self, feed_name):
        """Retrieves the feed, passes it to a parser, and then passes parsed observables to the workers

        :return:
        """
        if "feeds" not in self.feed_config.keys():
            return
        if feed_name not in self.feed_config['feeds']:
            return
        
        # These are fields that are used for control when parsing and should not be passed down to the observables
        fields_to_strip = ['node', 'map', 'values', 'pattern', 'remote', 'parser',
                           'username', 'password', 'method', 'start', 'end', 'interval']

#        for name in fields_to_strip:
#            if name in self.feed_config["feeds"][feed_name].keys():
#                pprint("{0} found in feed_config : {1}".format(name,feed_name))

        # Pull out parsing details for feeds from defined meta
        feed_parsing_details = dict((name, self.feed_config["feeds"][feed_name][name]) for name in fields_to_strip if name in self.feed_config["feeds"][feed_name].keys())
        feed_parsing_details['feed_name'] = feed_name

#        pprint(feed_parsing_details)

        # Exclude control fields from defined meta for created observables
        feed_meta = dict((name, self.feed_config["feeds"][feed_name][name]) for name in self.feed_config["feeds"][feed_name].keys() if name not in fields_to_strip)

        if "method" not in feed_parsing_details.keys():
            feed_parsing_details["method"] = "GET"

        if "parser" not in feed_parsing_details.keys():
            feed_parsing_details["parser"] = "regex"

        if "values" not in feed_parsing_details.keys():
            feed_parsing_details["values"] = ["observable"]
        elif not isinstance(feed_parsing_details["values"], list):
            feed_parsing_details["values"] = [feed_parsing_details["values"]]

        feed_parsing_details["journal"] = "{0}/{1}-{2}-{3}-journal.pickle".format(
            cif.CACHEDIR, os.path.basename(self.feed_file.lower()), feed_name.lower(),
            datetime.datetime.utcnow().strftime("%Y-%m-%d")
        )
        self.logging.debug("Built Journal Path: {0}".format(feed_parsing_details['journal']))

        if feed_parsing_details["remote"].startswith('/'):
            self.logging.debug("Local file detected '{0}'. Opening Locally.".format(feed_parsing_details["remote"]))
            temp = open(feed_parsing_details["remote"], "rb")
        else:
            self.logging.debug("Remote file detected '{0}'. Opening remotely.".format(
                feed_parsing_details["remote"])
            )
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/45.0.2454.93 Safari/537.36'
            }
            try:
                response = requests.request(feed_parsing_details["method"], feed_parsing_details["remote"],
                                            proxies=cif.proxies, stream=True, headers=headers, verify=False
                                            )
            except:
                self.logging.exception("Could not fetch remote url '{0}'".format(feed_parsing_details["remote"]))
                return

            if response.status_code > 300:
                self.logging.error("Failed fetching remote feed '{0}': {1} {2}".format(
                    feed_parsing_details["remote"], response.status_code, response.reason)
                )
                return

            temp = tempfile.TemporaryFile(mode="w+b")

            try:
                for chunk in response.iter_content(1024 * 1024):
                    temp.write(chunk)
            except:
                self.logging.exception("Could not read the content of remote url '{0}'".format(feed_parsing_details["remote"]))
                response.close()
                return
            response.close()

            self.logging.debug("Wrote {0} bytes to binary file.".format(temp.tell()))

            temp.seek(0)

        zip_file = None
        if zipfile.is_zipfile(temp):
            zip_file = zipfile.ZipFile(temp)
            temp_bin = zip_file.open(zip_file.namelist()[0])
        else:
            temp_bin = temp
            temp_bin.seek(0)

        if zip_file is None:
            test_header = temp.read(2)
            temp.seek(0)
            if test_header == b'\x1f\x8b':
                temp_bin = gzip.open(temp)
            else:
                temp_bin = temp

        file_to_parse = tempfile.TemporaryFile(mode="w+", encoding="ISO8859-1")
        while True:
            buf = temp_bin.read(1024 * 1024)
            if len(buf) == 0:
                break
            file_to_parse.write(buf.decode("ISO8859-1"))
        self.logging.debug("Wrote {0} bytes to text file.".format(file_to_parse.tell()))
        file_to_parse.seek(0)

        if zip_file is not None:
            zip_file.close()
        temp_bin.close()

        self.logging.debug("Creating Parser for feed {0}".format(feed_parsing_details['remote']))
        self.parser = Parser(parsing_details=feed_parsing_details, basemeta=feed_meta, file=file_to_parse)

        while self.parser.parsing:
            observables = self.parser.parsefile(2000)
            if len(observables) > 0:
                self.logging.debug("Feed '{0}' is sending {1} new objects to be processed".format(
                    feed_parsing_details['remote'], len(observables))
                )
                for observable in observables:
                    tasks.put(copy.deepcopy(observable))

        file_to_parse.close()
        self.logging.debug("Finished Parsing feed {0}".format(feed_parsing_details['remote']))

def dump(self, obj):
        '''return a printable representation of an object for debugging'''
        newobj=obj
        if '__dict__' in dir(obj):
            newobj=obj.__dict__
        if ' object at ' in str(obj) and not newobj.has_key('__type__'):
            newobj['__type__']=str(obj)
        for attr in newobj:
            newobj[attr]=self.dump(newobj[attr])
        return newobj
