# Create your views here.
import django.http as http
from django.db import transaction
import json
import httplib
from services.app import execute_create_project, execute_list_projects, execute_list_user_projects, \
    execute_change_project_status, execute_list_default_parameters, execute_create_project_parameter, \
    execute_list_project_parameters
from services.common import json_request_handler, getencdec
from services.models import Project
from svalidate import validate, OrNone, Any, DateTime, RegexpMatch, Equal

_good_string = RegexpMatch(r'^[^;:"''|\\/#@&><]*$')

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
    r = validate({'name' : _good_string,
                  'description' : OrNone(_good_string),
                  'begin_date' : OrNone(DateTime()),
                  'sharing' : True,
                  'ruleset' : Any(*[Equal(a[0]) for a in Project.PROJECT_RULESET]), # fucken amazing !
                  'user_name' : _good_string,
                  'user_id' : OrNone(''),
                  'user_description' : OrNone(_good_string)},
                 prs)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    result = execute_create_project(prs)
    r = http.HttpResponse(enc.encode(result))
    r.status_code = httplib.CREATED
    return r

@transaction.commit_on_success
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
    r = validate({'page_number' : OrNone(0),
                  'projects_per_page' : OrNone(0),
                  'status' : OrNone(Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])),
                  'begin_date' : OrNone(DateTime()),
                  'search' : OrNone(_good_string)},
                 pars)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    
    result = execute_list_projects(pars)
    r = http.HttpResponse(enc.encode(result))
    r.status_code=httplib.OK
    return r

@transaction.commit_on_success
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
    ret, st = execute_list_user_projects(params)
    return http.HttpResponse(enc.encode(ret), status=st)

@transaction.commit_on_success
@json_request_handler
def change_project_status_route(params):
    """
    get dictionary with keys:
    - `psid`: string, access key
    - `status`: status to change to, may be "opened", "planning", "contractor", "budget", "control", "closed"
    return no data
    Return status 200 if changed
    Return status 404 if no projecs or users found
    Return status 412(precondition failed) if given psid has no rights to change project or ruleset of project is not 'despot'
    Return 501(not implemented) if GET method was used
    Arguments:
    - `params`:
    """
    enc, dec = getencdec()
    r = validate({'psid' : '',
                  'status' : Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])},
                 params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    
    ret, st = execute_change_project_status(params)
    if st != httplib.OK:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st)
    
@transaction.commit_on_success
def list_default_parameters_route(request):
    """return default parameters
    request with any method and any body of request.
    Return status 200 everywhere. Body is json coded list of tables with keys:
    - `uuid`
    - `name`
    - `descr`
    - `tp`
    - `enum`: boolean 
    - `default`: string with value or null
    - `values': if enum is True, then list of tables with keys:
                                 -- `value`: enum value
                                 -- `caption`: caption
                                 | Otherwise none.
    """
    
    ret = execute_list_default_parameters()
    enc = json.JSONEncoder()
    return http.HttpResponse(enc.encode(ret))

@transaction.commit_on_success
@json_request_handler
def create_project_parameter_route(params):
    """Add project parameter by psid
    get parameters in body of request as json coded dict with keys:
    - `psid`:
    - `name`:
    - `descr`: string, may be null
    - `tp`:
    - `enum`: boolean
    - `value` : string, parameter value, may be null (if enum is true)
    - `values` : list if dictionaries with keys :
                                        -- `value`:
                                        -- `caption`:
                                      may be null if enum is false
    Return parameter id as just one string
    Return code is 201(created) if everything is ok
    Return code is 404 if user not found
    Return code is 412 if failed validtion of parameter, body will contain errors list
    Return code is 501 if request method was not POST
    """
    enc, dec = getencdec()
    r = validate({'psid' : _good_string,
                  'name' : _good_string,
                  'descr' : OrNone(_good_string),
                  'tp' : _good_string,
                  'enum' : True,
                  'value' : _good_string,
                  'values' : OrNone([{'value' : _good_string,
                                      'caption' : OrNone(_good_string)}])},
                 params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    if params['enum'] and (params.get('values') == None):
        return http.HttpResponse(u'if "enum" is true then "values" key must exist', status=httplib.PRECONDITION_FAILED)
    
    ret, stat = execute_create_project_parameter(params)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat)

@transaction.commit_on_success
@json_request_handler
def create_project_parameter_from_default_route(params):
    """create project parameter from default parameter given in request
    get json coded dictionary with keys:
    - `psid`:
    - `uuid`: default parameter uuid
    Return parameter id as just one string
    Return code is 201(created) if everything is ok
    Return code is 404 if user not found
    Return code is 412 if failed validtion of parameter, body will contain errors list
    Return code is 501 if request method was not POST
    Arguments:
    - `params`:
    """
    enc, dec = getencdec()
    r = validate({'psid' : _good_string,
                  'uuid' : _good_string},
                 params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    
    ret, st = execute_create_project_parameter_from_default(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st)
    
    

@transaction.commit_on_success
@json_request_handler
def list_project_parameters_route(params):
    """
    Read json coded data as one string with psid
    Return json coded list of dictionaries with keys:
    - `uuid`: parameter uuid
    - `name`: parameter name
    - `descr`: parameter description
    - `tp`: param type
    - `enum`: Boolean, enumerated value
    - `tecnical`: Boolean, True if parameter is tecnical
    - `values`: posible values of parameter, null if enum is false.
                List of dictionaries with keys:
                                          - `value`:
                                          - `caption`:
    - `value`: value of parameter, null if there is no one accepted value
    - `caption`: value description, null if `vote` is null
    - `votes`: list of dictionaries with keys:
                                          - `voter`: uuid of voter
                                          - `value`: value voted by user
                                          - `caption`: value description
                                          - `dt`: datetime of vote
    Return code 200 if everything is ok
    Return code 404 if no users found with given psid
    Arguments:
    - `params`:
    """
    enc = json.JSONEncoder()
    r = validate(_good_string, params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    ret, st = execute_list_project_parameters(params)
    return http.HttpResponse(enc.encode(ret), status=st)

@transaction.commit_on_success
@json_request_handler
def change_project_parameter_route(params):
    """
    Get json coded dictionary with keys:
    - `psid`:
    - `uuid`: parameter uuid
    - `value`: parameter value
    - `caption`: value caption, may be null
    Return status 200 if everything is ok
    Return status 404 if user with this `psid` not found
    Return status 412 when incorrect parameters, details with response body
    Arguments:
    - `params`:
    """
    enc = json.JSONEncoder()
    r = validate({'psid' : _good_string,
                  'uuid' : _good_string,
                  'value' : _good_string,
                  'caption' : OrNone(_good_string)},
                 params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    
    ret, st = execute_change_project_parameter(params)
    if st != httplib.OK:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st)

@transaction.commit_on_success
@json_request_handler
def conform_project_parameter_route(params):
    """
    get json encoded dictionary with keys:
    - `psid`:
    - `uuid`: string, parameter uuid
    Return code 201 if saved
    Return code 404 if user not found
    Return code 412 if other mistake
    Arguments:
    - `params`:
    """
    enc = json.JSONEncoder()
    r = validate({'psid' : _good_string,
                  'uuid' : _good_string},
                 params)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    
    ret, st = execute_conform_project_parameter(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st)

