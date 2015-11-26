__author__ = 'James DeVincentis <james.d@hexhost.net>'

import multiprocessing
import threading
import time
import datetime
import dateutil.parser
import queue

import cif

tasks = multiprocessing.Queue(262144)


class Thread(threading.Thread):
    def __init__(self, worker, name, q, backend, backendlock):
        threading.Thread.__init__(self)
        self.backend = backend
        self.backendlock = backendlock
        self.queue = q
        self.logging = cif.logging.getLogger("THREAD #{0}-{1}".format(worker, name))

    def run(self):
        """Runs in infinite loop waiting for items from this worker's queue. Each worker has 'cif.options.threads' of
        these running at any one given time.

        """
        self.logging.debug("Booted")
        while True:
            with self.backendlock:
                observable = self.queue.get()
                if observable is None:
                    break
                self.logging.debug("Thread Loop: Got observable")
    
                for name, meta in cif.worker.meta.meta.items():
                    self.logging.debug("Fetching meta using: {0}".format(name))
                    observable = meta(observable=observable)
    
                newobservables = []
                seen_observable = set()
                
                for name, plugin in cif.worker.plugins.plugins.items():
                    self.logging.debug("Running plugin: {0}".format(name))
                    result = plugin(observable=observable)
                    if result is not None:
                        for newobservable in result:
                            if "feed_dedup" in cif.options:
                                if newobservable.observable not in seen_observable:
                                    self.logging.debug("Found observable in the list : {0}".format(newobservable.observable))
                                    seen_observable.add(newobservable.observable)
                                    if newobservable.firsttime is None or not newobservable.firsttime:
                                        self.logging.debug("New observable seen, but firsttime is invalid, I will update it with : {0}".format(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")))
                                        newobservable.firsttime = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
                                    if newobservable.lasttime is None or not newobservable.lasttime:
                                        self.logging.debug("New observable seen, but lasttime is invalid, I will update it with : {0}".format(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")))
                                        newobservable.lasttime = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
                                    newobservables.append(newobservable)
                            else:
                                if newobservable.firsttime is None or not newobservable.firsttime:
                                    self.logging.debug("New observable seen, but firsttime is invalid, I will update it with : {0}".format(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")))
                                    newobservable.firsttime = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
                                if newobservable.lasttime is None or not newobservable.lasttime:
                                    self.logging.debug("New observable seen, but lasttime is invalid, I will update it with : {0}".format(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")))
                                    newobservable.lasttime = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ")
                                newobservables.append(newobservable)    


                for name, meta in cif.worker.meta.meta.items():
                    for key, o in enumerate(newobservables):
                        self.logging.debug("Fetching meta using: {0} for new observable: {1} having data : {2}".format(name, key, o.observable))
                        newobservables[key] = meta(observable=o)
    
                newobservables.insert(0, observable)
                self.logging.debug("Sending {0} observables to be created.".format(len(newobservables)))
    
                try:          
                    if "feed_dedup" in cif.options:        
                        for newobservable in reversed(newobservables):
                            param = {"observable" : newobservable.observable}
                            found_observables, index, _id = self.backend.observable_search(param, _from="worker")
                            if found_observables:
                                self.logging.debug("Seen duplicated observable ({0} with id {1}), updating the lasttime field..".format(newobservable.observable, newobservable._id))
                                self.backend.observable_update("lasttime", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%I:%SZ"), _id, index)
                                newobservables.remove(newobservable)
                    if newobservables:
                        self.backend.observable_create(newobservables)
                finally:
                    self.logging.debug("worker Loop: End")

class QueueManager(threading.Thread):
    def __init__(self, worker, source, destination):
        threading.Thread.__init__(self)
        self.source = source
        self.destination = destination
        self.worker = worker
        self.die = False
        self.logging = cif.logging.getLogger("Manager #{0}".format(worker))

    def run(self):
        """Runs in an infinite loop taking any tasks from the main queue and distributing it to the workers. First one
        to grab it from the main queue wins. Each worker process has one of these threads.

        """
        while True:
            self.logging.debug("Waiting for item from global queue: {0}".format(repr(self.source)))
            observable = self.source.get()
#            self.logging.debug("Got {0} from global queue: {1}".format(repr(observable), observable.observable))
            if observable is None:
                for i in range(1, cif.options.threads+1):
                    self.logging.error("Mudering my threads")
                    self.destination.put(None)
                self.die = True
                break
            else:
                self.logging.debug("Put {0} into local queue: {1}".format(repr(observable), observable.observable))
                self.destination.put(observable)


class Process(multiprocessing.Process):
    def __init__(self, name):
        multiprocessing.Process.__init__(self)
        self.backend = None
        self.backendlock = threading.Lock()
        self.name = name
        self.logging = cif.logging.getLogger("worker #{0}".format(name))
        self.queue = queue.Queue(cif.options.threads*2)
        self.threads = {}

    def run(self):
        """Connects to the backend service, spawns and threads off into worker threads that hadnle each observable. One
        backend service connection is shared per thread however each connection *is* automatically thread safe due to
        the backend lock.

        """

        self.logging.info("Starting")

        backend = __import__("cif.backends.{0:s}".format(cif.options.storage.lower()),
                             fromlist=[cif.options.storage.title()]
                             )
        self.logging.debug("Initializing Backend {0}".format(cif.options.storage.title()))

        self.backend = getattr(backend, cif.options.storage.title())()
        self.logging.debug("Connecting to Backend {0}".format(cif.options.storage_uri))

        self.backend.connect(cif.options.storage_uri)
        self.logging.debug("Connected to Backend {0}".format(cif.options.storage_uri))

        backend_installed = True

        self.threads = {}
        queuemanager = None

        self.logging.info("Entering worker loop")
        while True:
            if queuemanager is None or not queuemanager.is_alive():
                # Check to see if the queue manager got a poison pill. We don't manage the queue directly so we trust
                #   the queue manager to see if it got one.
                if queuemanager is not None and queuemanager.die:
                    break
                queuemanager = QueueManager(self.name, tasks, self.queue)
                queuemanager.start()
            self.logging.debug("Local Queue Size: {0}".format(self.queue.qsize()))
        
            for i in range(1, cif.options.threads+1):
                if i not in self.threads or self.threads[i] is None or not self.threads[i].is_alive():
                    self.threads[i] = Thread(self.name, str(i), self.queue, self.backend, self.backendlock)
                    self.threads[i].start()
                
            
            time.sleep(5)
