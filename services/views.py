# Create your views here.
import django.http as http
import json
import httplib
from services.app import precheck_create_project, execute_create_project

def getencdec():
    """return json encoder and decoder
    """
    return (json.JSONEncoder(), json.JSONDecoder())

def create_project_route(request):
    """Creates project in database
    Handles just POST requests.
    Parameters must be hash table in json format sent in request body.
    Acceptable keys are:
    - `name`: name of new project
    - `description`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `shared` : Boolean
    - `ruleset` : string with ruleset name, may be 'despot'
    - `user_name` : string, name of user
    - `user_id` : external user id to bind participant with user
    - `user_description`: string, description of user. May be null
    Return data in response body in json format:
    - `project_uuid` : string, universal identificator for project
    - `psid` : string, access key for new participant
    - `token` : string, access key for "magic link"
    Return status 201(created) if project is created
    Return status 412(precondition failed) if parameters are wrong, body will contain details
    Otherwise return 500
    """
    if request.method == 'POST':
        enc, dec = getencdec()
        prs = dec.decode(request.read())
        errs = precheck_create_project(prs)
        if len(errs) > 0:
            r = http.HttpResponse(enc.encode(errs))
            r.status_code = httplib.PRECONDITION_FAILED
            return r
        result = execute_create_project(prs)
        r = http.HttpResponse(e.encode(result))
        r.status_code = httplib.CREATED
        return r
    else:
        raise http.Http404
