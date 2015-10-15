__author__ = 'James DeVincentis <james.d@hexhost.net>'


class Backend(object):

    # Connects to backend storage
    def connect(self, connect_string):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Disconnects from backend storage
    def disconnect(self):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Ping
    def ping(self):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Searches observables
    def observable_search(self, params, start=None, number=None, _from=None):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Creates a new observable
    def observable_create(self, observable):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Update an observable
    def observable_update(self, field, value, index):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Cleans observables older than date
    def observable_clean(self, date):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Gets a token
    def token_get(self, token_id):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Puts a new token in the backend
    def token_create(self, token):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Deletes a token in the backend
    def token_delete(self, token):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Edits a token in the backend
    def token_update(self, tokens):
        raise NotImplementedError("This must be implemented in the backend storage class")

    # Lists tokens
    def token_list(self, start=None, number=None):
        raise NotImplementedError("This must be implemented in the backend storage class")
