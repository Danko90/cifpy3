__author__ = 'James DeVincentis <james.d@hexhost.net>'

import multiprocessing
import threading
import queue
import time

import cif

tasks = multiprocessing.Queue(131072)


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
            #self.backendlock.acquire() 
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
                
#               self.backendlock.acquire()
                
                
                for name, plugin in cif.worker.plugins.plugins.items():
                    self.logging.debug("Running plugin: {0}".format(name))
                    result = plugin(observable=observable)
                    if result is not None:
                        for newobservable in result:
                            if newobservable.observable not in seen_observable:
                                self.logging.debug("Found observable in the list : {0}".format(newobservable.observable))
                                seen_observable.add(newobservable.observable)
                                newobservables.append(newobservable)
    
    
                for name, meta in cif.worker.meta.meta.items():
                    for key, o in enumerate(newobservables):
                        self.logging.debug("Fetching meta using: {0} for new observable: {1} having data : {2}".format(name, key, o.observable))
                        newobservables[key] = meta(observable=o)
    
                newobservables.insert(0, observable)
                self.logging.debug("Sending {0} observables to be created.".format(len(newobservables)))
    
                try:          
                    for newobservable in reversed(newobservables):
                        param = {"observable" : newobservable.observable}
                        found_observables = self.backend.observable_search(param)
                        if found_observables:
                            newobservables.remove(newobservable)
                    self.backend.observable_create(newobservables)
                finally:
#                # Make sure to release the lock even if we encounter but don't trap it. But if you use with you don't need to release the lock
#                self.backendlock.release()
                    self.logging.debug("worker Loop: End")

class QueueManager(threading.Thread):
    def __init__(self, worker, source, destination):
        threading.Thread.__init__(self)
        self.source = source
        self.destination = destination
        self.worker = worker
        self.die = False

    def run(self):
        """Runs in an infinite loop taking any tasks from the main queue and distributing it to the workers. First one
        to grab it from the main queue wins. Each worker process has one of these threads.

        """
        while True:
            observable = self.source.get()
            if observable is None:
                for i in range(1, cif.options.threads+1):
                    self.destination.put(None)
                self.die = True
                break
            else:
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

            for i in range(1, cif.options.threads+1):
                if i not in self.threads or self.threads[i] is None or not self.threads[i].is_alive():
                    self.threads[i] = Thread(self.name, str(i), self.queue, self.backend, self.backendlock)
                    self.threads[i].start()

            time.sleep(5)
