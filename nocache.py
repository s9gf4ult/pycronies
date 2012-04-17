from django.utils.cache import patch_vary_headers
from django.utils.http import cookie_date
from django.utils.importlib import import_module

class NoCache(object):
    def process_response(self, request, response):
        """
        set the "Cache-Control" header to "must-revalidate, no-cache"
        """
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'must-revalidate, no-cache'
        return response
