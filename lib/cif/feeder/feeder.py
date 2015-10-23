__author__ = 'James DeVincentis <james.d@hexhost.net>'

import os
import multiprocessing
import time

import schedule

import cif


class Feeder(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.backend = None
        self.logging = cif.logging.getLogger('FEEDER')
        self.logging.info("Loading Feeds")
        self.load_feeds()

    def load_feeds(self):
        schedule.clear()
        feeds = {}
        self.logging.debug("Getting List of Feeds")
        files = os.listdir(cif.options.feed_directory)
        feed_files = []
        for file in files:
            if file.endswith(".yml"):
                self.logging.debug("Found Feed File: {0}".format(file))
                feed_files.append(os.path.join(cif.options.feed_directory, file))

        feed_files.sort()
        for feed_file in feed_files:
            self.logging.info("Loading Feed File: {0}".format(feed_file))
            feeds[feed_file] = cif.feeder.Feed(feed_file)
            self.logging.info("Scheduling Feed File:".format(feed_file))
            if 'feeds' not in feeds[feed_file].feed_config:
                continue
            for feed_name in feeds[feed_file].feed_config['feeds'].keys():
                if "interval" in feeds[feed_file].feed_config['feeds'][feed_name]:
                    if feeds[feed_file].feed_config['feeds'][feed_name]['interval'] == "hourly":
                        self.logging.error(repr(schedule.every().hour.at("00:00").do(feeds[feed_file].process, feed_name)))
                    elif feeds[feed_file].feed_config['feeds'][feed_name]['interval'] == "daily":
                        self.logging.error(repr(schedule.every().day.at("00:00").do(feeds[feed_file].process, feed_name)))
                    elif feeds[feed_file].feed_config['feeds'][feed_name]['interval'] == "weekly":
                        self.logging.error(repr(schedule.every().day.at("00:00").do(feeds[feed_file].process, feed_name)))
                    else:
                        self.logging.error(repr(schedule.every(1).minute.do(feeds[feed_file].process, feed_name)))
    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
