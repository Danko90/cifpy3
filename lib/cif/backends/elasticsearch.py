__author__ = 'James DeVincentis <james.d@hexhost.net>'

import http.client
import json
import socket
import os

import datetime
import dateutil.parser
import cif

from . import Backend


class Elasticsearch(Backend):
    def __init__(self):
        self.conn = None
        self.logging = cif.logging.getLogger('ElasticSearch')
        self.installed = False

    def connect(self, connect_string):
        """Connects to the backend and performs a basic status check

        :param str connect_string: well formed URL for the ElasticSearch HTTP API
        :raises NotImplementedError:
        """
        socket.setdefaulttimeout(180)

        if "://" in connect_string:
            (method, url) = connect_string.split("://")
        else:
            method = 'http'
            url = connect_string

        if method == "http":
            self.conn = http.client.HTTPConnection(url)
        elif method == "https":
            self.conn = http.client.HTTPSConnection(url)
        else:
            raise NotImplementedError("Connection Protocol {0:s} not supported".format(method))

        self._request()

    def disconnect(self):
        """Disconnects from the backend storage.

        """
        self.conn.close()

    def ping(self):
        """Handles a ping request to the backend. This can be useful for checking if it's still alive

        :raises: RuntimeError
        """
        try:
            self._request()
        except Exception as e:
            raise RuntimeError("Ping failed") from e

    def observable_search(self, params, start=None, number=None, _from=None, count_only=False):
        """Uses a list of parameters to build a query and then return the objects from the ElasticSearch backend

        :param dict params: Parameters to use to build the search string
        :param start: Record number to start at. If None is determined by ElasticSearch
        :type start: None or int
        :param number: Number of records to retrieve starting at :py:attr:`start`
        :type number: None or int
        :param _from: string that indicates where the call comes from
        :param boolean count_only: indicator to only return a count and not objects
        :return: List of retrieved observable objects (cif.type.Observable)
        :rtype: list
        :raises: LookupError
        :raises: RuntimeError
        """
        query = self._build_search_string(params, count_only=count_only)
        result = []

        if start is not None:
            query["from"] = start

        if number is not None:
            query["size"] = number

        try:
            if count_only:
                result = self._request(path='/cif.observables-*/observables/_count', body=query)
            else:
                result = self._request(path='/cif.observables-*/observables/_search', body=query)
        except Exception as e:
            i = 0
            for i in range(3):
                try:
                    result = self._request(path='/cif.observables-*/observables/_search', body=query)
                    time.sleep(3)
                    if result:
                        break
                except Exception as e:
                    continue
            if not result: 
                raise LookupError("Failed to get observables.") from e

        if count_only:
            if "count" not in result.keys():
                raise RuntimeError("Not a properly formatted Elasticsearch count result")
            return result['count']

        if "hits" not in result.keys():
            raise RuntimeError("Not A properly formatted Elasticsearch result")

        observables = []

        if len(result["hits"]["hits"]) == 0:
            if _from is None:
                raise LookupError("No results from observable search")
            else:
                return observables, None, None

        for hit in result["hits"]["hits"]:
            index = hit["_index"]
            _id = hit["_id"]

        for hit in result["hits"]["hits"]:
            observables.append(self._object('observable', hit["_source"]))

        self.logging.debug("Result search : {0}".format(result))

        return observables, index, _id
    
    def observable_update(self, field, value, observable_id, index):
        """ Update a document
        :param field: name of the field 
        :param value: value 
        """
        data = []

        data.append({"update": {"_index": index, "_type": "observables", "_id": observable_id}})

        data.append({"doc": {field : value}})

        self.logging.debug("Update : {0} for index {1}".format(data, observable_id))

        result = self._request(path='{0}/observables/_bulk'.format(index), body=data, method='POST')
        results = []

        for tmp in result["items"]:
            if "error" in tmp.keys():
                results.append((False, tmp.error))
            else:
                results.append((True, "success"))

        self.logging.debug("Result update : {0}".format(results))

        return results

    def observable_clean(self, date):
        """Deletes all observables older than date
        
        :param date datetime: a datetime object. Use this as a point of reference for deleting objects older than this date
        """
        result = self._request(path='/_aliases')
        for index in result.keys():
            if index.startswith("cif.observables-"):
                (year,month,day) = index.replace("cif.observables-", "").split(".")
                index_date = datetime.datetime(int(year), int(month), int(day))
                if index_date < date:
                    # Delete the index
                    self._request(path='/{0}'.format(index), method="DELETE")
        
    def observable_create(self, observables):
        """Creates a new observable or list of observables using the ElasticSearch bulk API

        :param observables: a single or list of cif.types.Observable objects to be created
        :type observables: list[cif.types.Observable] or cif.types.Observable
        :return: List of tuples. Tuple contains a boolean indicating success or failure and a message
        :rtype: list
        """
        if not isinstance(observables, list):
            observables = [observables]

        data = []
        for index, observable in enumerate(observables):
            data.append({"create": {"_index": "cif.observables-{0}".format(
                datetime.datetime.utcnow().strftime("%Y.%m.%d")
            ), "_type": "observables", "_id": observable.id}})

            d = observable.todict()
            d["@timestamp"] = d["timestamp"]
            data.append(d)

#        self.logging.debug("Create request : {0}".format(data))
        result = self._request(path='/_bulk', body=data, method='POST')

        results = []

        for tmp in result["items"]:
            if "error" in tmp.keys():
                results.append((False, tmp.error))
            else:
                results.append((True, "success"))

        return results

    def token_create(self, tokens):
        """Creates a new token or list of tokens using the ElasticSearch bulk API

        :param tokens: a single or list of cif.types.Token objects to be created
        :type tokens: list[cif.types.Token] or cif.types.Token
        :return: List of tuples. Tuple contains a boolean indicating success or failure and a message
        :rtype: list
        """
        data = []

        if not isinstance(tokens, list):
            tokens = [tokens]

        for key, token in enumerate(tokens):
            data.append({"create": {"_index": "cif.tokens", "_type": "tokens", "_id": token.token}})
            data.append(token.todict())
        result = self._request(path='/_bulk', body=data, method='POST')
        results = []
        for tmp in result["items"]:
            if "error" in tmp.keys():
                results.append((False, tmp.error))
            else:
                results.append((True, "success"))
        return results

    def token_delete(self, token_id):
        """Deletes a token object

        :param str token_id: Token id to be deleted
        :raises: RuntimeError
        """
        try:
            return self._request(path='/cif.tokens/tokens/{0:s}'.format(token_id), method='DELETE')
        except Exception as e:
            raise RuntimeError("Token could not be deleted.") from e

    def token_update(self, tokens):
        """Updates a token object

        :param tokens: a single or list of cif.types.Token objects to be updated
        :type tokens: list[cif.types.Token] or cif.types.Token
        :return: List of tuples. Tuple contains a boolean indicating success or failure and a message
        :rtype: list
        """
        data = []

        if not isinstance(tokens, list):
            tokens = [tokens]

        for index, token in enumerate(tokens):
            data.append({"update": {"_index": "cif.tokens",
                                    "_type": "tokens", "_id": token.token}})
            data.append({"doc": token.__diff__})

        result = self._request(path='/_bulk', body=data, method='POST')

        results = []

        for tmp in result["items"]:
            if "error" in tmp.keys():
                results.append((False, tmp.error))
            else:
                results.append((True, "success"))
        return results

    def token_list(self, start=None, number=None):
        """Returns a list of tokens

        :param start: Record number to start at. If None is determined by ElasticSearch
        :type start: None or int
        :param number: Number of records to retrieve starting at :py:attr:`start`
        :type number: None or int
        :return: List of retrieved token objects (cif.type.Token)
        :rtype: list
        :raises: LookupError
        :raises: RuntimeError
        """
        query = {"query": {"match_all": {}}}

        if start is not None:
            query["from"] = start

        if number is not None:
            query["size"] = number

        try:
            result = self._request(path='/cif.tokens/tokens/_search', body=query)
        except:
            raise RuntimeError("Failed to get a token.")

        if "hits" not in result.keys():
            raise RuntimeError("Not an elasticsearch result")

        if not len(result["hits"]["hits"]):
            raise LookupError("Tokens not found")

        tokens = []
        for hit in result["hits"]["hits"]:
            tokens.append(self._object('token', hit["_source"]))
        return tokens

    def token_get(self, token_id):
        """Retrieves token and returns it using the token_id

        :param str token_id: A 64 character token ID
        :return: A token object
        :rtype: cif.types.Token
        :raises: RuntimeError
        :raises: LookupError
        """

        try:
            result = self._request(path='/cif.tokens/tokens/_search',
                                   body={"query": {"query_string": {"default_field": "token", "query": token_id}}})
        except Exception as e:
            raise RuntimeError("Failed to get a token.") from e

        if "hits" not in result.keys():
            raise RuntimeError("Not an elasticsearch result")

        if not len(result["hits"]["hits"]):
            raise LookupError("Token not found")

        return self._object('token', result["hits"]["hits"][0]["_source"])

    @staticmethod
    def _object(object_type, params):
        """Instantiates an object of `object_type` using `params` and then return it

        :param str object_type: cif.types type. (observable,token)
        :param dict params: Attributes to pass to the object when instantiating it
        :return: initialized object of `object_type`
        :rtype: cif.types.Observable or cif.types.Token
        """
        mod = __import__("cif.types.{0:s}".format(object_type.lower()), fromlist=[object_type.title()])
        obj = getattr(mod, object_type.title())
        params_to_delete = []
        for param in params:
            if param.startswith("@"):
                params_to_delete.append(param)
        for param in params_to_delete:
            del params[param]
        return obj(params, validation=False)

    def _request(self, path='/', body=None, method="GET"):
        """Send a request to the ElasticSearch API

        :param str path: URL Path
        :param body: HTTP request body to send
        :type body: list or dict
        :param str method: HTTP request method to use
        :return: Parsed JSON data
        :rtype: dict of dict or list of dict of dict
        :raises: RuntimeError
        :raises: TimeoutError
        """

        args = [path]

        if body is not None:
            if isinstance(body, list):
                tmp = ""
                for key, line in enumerate(body):
                    tmp += json.dumps(line) + "\n"
                args.append(tmp)
            else:
                args.append(json.dumps(body))

        try:
            self.conn.request(method, *args)
        except Exception as e:
            self.conn.close()
            raise RuntimeError("Backend storage timed out responding : {0}.".format(type(e))) from e

        try:
            result = self.conn.getresponse()
        except Exception as e:
            self.conn.close()
            raise RuntimeError('Backend error getting response.') from e

        if result.status >= 400:
            self.conn.close()
            raise RuntimeError("Backend error. Got '{0:d} {1:s}' status from the backend.".format(result.status, result.reason))

        try:
            data = result.read().decode('ISO8859-1')
        except Exception as e:
            self.conn.close()
            raise RuntimeError("Backend error. Couldn't read result from request") from e

        try:
            data = json.loads(data)
        except Exception as e:
            self.conn.close()
            raise RuntimeError("Backend error. Couldn't load JSON data from request:") from e

        if "timed_out" in data.keys() and data["timed_out"]:
            raise TimeoutError("Backend error. Query timed out")

        return data

    @staticmethod
    def _build_search_string(params, count_only=False):
        """Builds an ElasticSearch compatible search string

        :param dict params: Parameters to use for a search
        :return: ElasticSearch compatible search string
        :rtype: dict
        """

        # Params that will be searched in a range with greater than or equal to
        gte_params = ['confidence', 'firsttime', 'reporttime', 'timestamp']

        # Params that will be search in a range with less than or equal to
        lte_params = ['lasttime', 'reporttimeend', 'timestampend']

        # Params that must be a list if present
        list_params = ['tags', 'description', 'application', 'asn', 'provider', 'rdata', 'group']

        for param in list_params:
            if param in params:
                if not isinstance(params[param], list):
                    params[param] = [params[param]]

        a = []
        neg = []
        for param, value in params.items():
            if param not in lte_params and param not in gte_params:
                if isinstance(value, list):
                    if param in ['group', 'tags']:
                        a.append({"or": [{"term": {param: v}} for v in value if not v.startswith('!')]})
                    else:
                        a.append({"and": [{"term": {param: v}} for v in value if not v.startswith('!')]})
                    for v in value:
                        if v.startswith('!'):
                            neg.append({"term": {param: v[1:]}})
                else:
                    if value.startswith('!'):
                        neg.append({"term": {param: value[1:]}})
                    else:
                        a.append({"term": {param: value}})
            elif param in lte_params:
                if param.endswith('end'):
                    param = param[:-3]
                a.append({"range": {param: {"lte": value}}})
            elif param in gte_params:
                a.append({"range": {param: {"gte": value}}})
        if len(neg):
            a.append({"not": {"filter": {"and": neg}}})
        if count_only:
            return {"query": {"filtered": {"filter": {"and": a}}}}
        return {"query": {"filtered": {"filter": {"and": a}}}, "sort": [{'@timestamp': {"order": "desc"}}]}

    def uninstall(self):
        """Uninstalls Indexes

        """
        self._request(path='/cif.*', method="DELETE")

    def clear(self):
        """Clears data from observables indexes

        """
        self._request(path='/cif.observables-*', method="DELETE")

    def install(self):
        """Install indexes into ElasticSearch

        """
        if self.installed is not True:
            observables = {"template": "cif.observables-*",
                           "mappings": {
                               "observables": {
#                                   "dynamic" : "strict",
                                   "properties": {
                                       "@version": {
                                           "index": "not_analyzed",
                                           "type": "string"
                                       },
                                       "@timestamp": {
                                           "type": "date"
                                       },
                                       "group": {
                                           "type": "string",
                                           "index": "not_analyzed"
                                       },
                                       "observable": {
                                           "type": "string",
                                           "index": "not_analyzed"
                                       },
                                       "otype": {
                                           "type": "string"
                                       },
                                       "confidence": {
                                           "type": "float",
                                           "store": "yes"
                                       },
                                       "firsttime": {
                                           "type": "date"
                                       },
                                       "lasttime": {
                                           "type": "date"
                                       },
                                       "reporttime": {
                                           "type": "date"
                                       },
                                       "provider": {
                                           "type": "string",
                                           "index": "not_analyzed"
                                       },
                                       "rdata": {
                                           "type": "string",
                                           "index": "not_analyzed"
                                       },
                                       "cc": {
                                           "type": "string"
                                       },
                                       "portlist": {
                                           "type": "integer"
                                       },
                                       "latitude": {
                                           "type": "double"
                                       },
                                       "longitude": {
                                           "type": "double"
                                       },
                                       "geolocation": {
                                           "type": "geo_point"
                                       }
                                   }
                               }
                           }
                           }
    
            # Tokens data structure
            tokens = {"template": "cif.tokens-*",
                      "mappings": {
                          "tokens": {
                              "properties": {
                                  "@version": {
                                      "index": "not_analyzed",
                                      "type": "string"
                                  },
                                  "@timestamp": {
                                      "type": "date",
                                      "format": "date_time"
                                  },
                                  "username": {
                                      "type": "string",
                                      "index": "not_analyzed"
                                  },
                                  "groups": {
                                      "type": "string"
                                  },
                                  "token": {
                                      "type": "string"
                                  },
                                  "revoked": {
                                      "type": "boolean"
                                  },
                                  "read": {
                                      "type": "boolean"
                                  },
                                  "write": {
                                      "type": "boolean"
                                  },
                                  "acl": {
                                      "type": "string"
                                  },
                                  "expires": {
                                      "type": "long"
                                  }
                              }
                          }
                      }
                      }
    
            # Make the requests to install the templates
            self._request('/_template/cif_observables/', observables, 'PUT')
            self._request('/_template/cif_tokens/', tokens, 'PUT')
            self.logging.debug("Installing mapping")
            self.installed = True

