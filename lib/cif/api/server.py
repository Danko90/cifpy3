__author__ = 'James DeVincentis <james.d@hexhost.net>'

import http.server
import socketserver
import multiprocessing
import sys

import setproctitle

import cif


class HTTPServer(socketserver.ForkingMixIn, http.server.HTTPServer):
    def __init__(self, *args, **kwargs):
        http.server.HTTPServer.__init__(self, *args, **kwargs)

        self.logging = cif.logging.getLogger('APIHTTP')


class Server(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.logging = cif.logging.getLogger('api')
        self.logging.debug("Initialized api Server")

    def run(self):
        try:
            setproctitle.setproctitle('[CIF-SERVER] - API Server')
        except:
            pass
        self.logging.info("Starting api Server")
        # Run the api server
        server = HTTPServer((cif.options.host, cif.options.port), cif.api.Handler)
        server.serve_forever()
        sys.exit()
