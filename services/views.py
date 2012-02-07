# Create your views here.
import django.http as http
from django.db import transaction
import json
import httplib
from services.app import precheck_create_project, execute_create_project

def getencdec():
    """return json encoder and decoder
    """
    return (json.JSONEncoder(), json.JSONDecoder())

@transaction.commit_on_success
def create_project_route(request):
    """Creates project in database
    Handles just POST requests.
    Parameters must be hash table in json format sent in request body.
    Acceptable keys are:
    - `name`: name of new project
    - `description`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `sharing` : Boolean
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
    Return status 404 if method was not POST
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
        r = http.HttpResponse(enc.encode(result))
        r.status_code = httplib.CREATED
        return r
    else:
        raise http.Http404


def list_projects_route(request):
    """Return list of projects which parameters suit to query
    query is json formated table with keys:
    - `page_number`: number of page to get, if null return first page
    - `projects_per_page`: number of projects per one page, if null return all projects
    - `status`: status of projects to return, if null return projects of any status
    - `begin_date`: the earliest date for project to return
    - `search`: string to search projects by name or description
    Return list, table values are:
    - `uuid`: string with uuid of project
    - `name`: name of project
    - `descr`: description of project
    - `begin_date`: datetime table, begin date of project
    return code 200 if everithin is ok
    return code 412 if wring parameter got
    return code 404 if GET method tried
    """
    if request.method == 'POST':
        enc,dec = getencdec()
        rc = request.read()
        try:
            pars = dec.decode(rc)
        except:
            pars={}
        errs = precheck_list_projects(pars)
        if len(errs) > 0:
            rt = http.HttpResponse(enc.encode(errs))
            rt.status_code = httplib.PRECONDITION_FAILED
            return rt
        result = execute_list_projects(pars)
        r = http.HttpResponse(enc.encode(result))
        r.status_code=httplib.OK
        return r
    raise http.Http404
