# Create your views here.
import django.http as http
from django.db import transaction
import json
import httplib
from services.app import precheck_create_project, execute_create_project, \
    precheck_list_projects, execute_list_projects
from services.common import json_request_handler, getencdec

@transaction.commit_on_success
@json_request_handler
def create_project_route(prs):
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
    Return status 501(not implemented) if method was not POST
    Otherwise return 500
    """
    enc, dec = getencdec()
    errs = precheck_create_project(prs)
    if len(errs) > 0:
        r = http.HttpResponse(enc.encode(errs))
        r.status_code = httplib.PRECONDITION_FAILED
        return r
    result = execute_create_project(prs)
    r = http.HttpResponse(enc.encode(result))
    r.status_code = httplib.CREATED
    return r

@json_request_handler
def list_projects_route(pars):
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
    return code 501(not implemented) if GET method tried
    """
    enc,dec = getencdec()
    errs = precheck_list_projects(pars)
    if len(errs) > 0:
        rt = http.HttpResponse(enc.encode(errs))
        rt.status_code = httplib.PRECONDITION_FAILED
        return rt
    result = execute_list_projects(pars)
    r = http.HttpResponse(enc.encode(result))
    r.status_code=httplib.OK
    return r

@json_request_handler
def list_user_projects_route(params):
    """return list of projects assigned to user
    get one string with user_id to ger projects
    Return list of tables with keys:
    - `uuid`: uuid of project
    - `name`: name of project
    - `descr` :description of project
    - `begin_date`: datetime table
    - `initiator` boolean, if user is initiator
    - `status`: string, project status
    Return status 200 if everithing ok
    Return status 404 (not found) if no one user found
    Return status 501 if GET method was called
    Arguments:
    - `request`:
    """
    enc, dec = getencdec()
    if not isinstance(params, basestring):
        return http.HttpResponse(enc.encode([u'You must give just one string, not {0}'.format(params)]), status=httplib.PRECONDITION_FAILED)
    
        
