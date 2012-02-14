# Create your views here.
# -*- coding: utf-8 -*-

import django.http as http
from django.db import transaction
import json
import httplib
from services.app import execute_create_project, execute_list_projects, execute_list_user_projects, \
    execute_change_project_status, execute_list_default_parameters, execute_create_project_parameter, \
    execute_list_project_parameters, execute_create_project_parameter_from_default
from services.common import json_request_handler, getencdec
from services.models import Project
from svalidate import validate, OrNone, Any, DateTime, RegexpMatch, Equal

_good_string = RegexpMatch(r'^[^;:"''|\\/#@&><]*$')

@transaction.commit_on_success
@json_request_handler
def create_project_route(prs):
    """
    **Create project**
    
    address to query **/project/create**

    The body of query must contain dictionary with keys:
    
    - `name`: name of new project
    - `descr`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `sharing`: Boolean
    - `ruleset`: string with ruleset name, may be 'despot'
    - `user_name`: string, name of user
    - `user_id`: external user id to bind participant with user
    - `user_description`: string, description of user. May be null
    
    Return dictionary with keys:
    
    - `project_uuid` : string, universal identificator for project
    - `psid` : string, access key for new participant
    - `token` : string, access key for "magic link"

    Posible return http status:

    - `201`: project is created
    - `412`: precondition failed, project was not created because of wrong data details in response body
    - `501`: query was not post
    - `500`: otherwise
    """
    enc, dec = getencdec()
    r = validate({'name' : _good_string,
                  'descr' : OrNone(_good_string),
                  'begin_date' : OrNone(DateTime()),
                  'sharing' : True,
                  'ruleset' : Any(*[Equal(a[0]) for a in Project.PROJECT_RULESET]), # fucken amazing !
                  'user_name' : _good_string,
                  'user_id' : OrNone(''),
                  'user_descr' : OrNone(_good_string)},
                 prs)
    if r != None:
        return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
    result, stat = execute_create_project(prs)
    if stat != httplib.CREATED:
        transaction.rollback()
    r = http.HttpResponse(enc.encode(result))
    r.status_code = stat
    return r

@transaction.commit_on_success
@json_request_handler
def list_projects_route(pars):
    """
    **List Projects**

    address to query: **/project/list**
    
    Return list of projects which parameters suit to query
    query is json formated dictionary with keys:
    
    - `page_number`: number of page to get, if null return first page
    - `projects_per_page`: number of projects per one page, if null return all projects
    - `status`: status of projects to return, if null return projects of any status
    - `begin_date`: the earliest date for project to return
    - `search`: string to search projects by name or description
    
    Return list of dictionaries with keys:
    
    - `uuid`: string with uuid of project
    - `name`: name of project
    - `descr`: description of project
    - `begin_date`: datetime table, begin date of project

    Posible return status:

    - `200`: ok
    - `412`: precondition failed, details in response body
    - `501`: query was not post
    - `500`: otherwise
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
    """
    **List Projects assigned to user**

    address to query: **/project/list/userid**

    Get one string with user_id
    
    Return list of tables with keys:
    
    - `uuid`: uuid of project
    - `name`: name of project
    - `descr` :description of project
    - `begin_date`: datetime table
    - `initiator` boolean, if user is initiator
    - `status`: string, project status

    Posible return status:
    
    - `200`: ok
    - `412`: precondition failed, details in response body
    - `501`: query was not post
    - `500`: otherwise
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
    **Change project status**

    address to query: **/project/status/change**
    
    Get dictionary with keys:
    
    - `psid`: string, access key
    - `status`: status to change to, may be "opened", "planning", "contractor", "budget", "control", "closed"
    
    Return no data

    Posible return status:
    
    - `200`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
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
    """
    **List default parameters**

    address to query: **/parameters/list**

    Get no data
    
    Return list of dictionaries with keys:
    
    - `uuid`: parameter uuid
    - `name`: parameter name
    - `descr`: parameter description
    - `tp`: type of parameter 
    - `enum`: (boolean) parameter is enumerable
    - `default`: string with default parameter value
    - `values`: if `enum` list of dictionaries with keys:
       - `value`: one of posible values
       - `caption`: value description

    Return status:
    
    - `200`: ok
    - `500`: otherwise
    """
    
    ret = execute_list_default_parameters()
    enc = json.JSONEncoder()
    return http.HttpResponse(enc.encode(ret))

@transaction.commit_on_success
@json_request_handler
def create_project_parameter_route(params):
    """
    **Create project parameter**

    address to query **/project/parameter/create**

    Get parameters in body of request as json coded dictionary with keys:
    
    - `psid`: access key
    - `name`: name of parameter
    - `descr`: string, may be null
    - `tp`: type of parameter
    - `enum`: boolean
    - `value`: string, parameter value, may be null
    - `values`: list if dictionaries with keys :
       - `value`: one of posible values of parameter
       - `caption`: value description
      
    Posible return status:

    - `201`: project parameter was created
    - `412`: precondition failed, details in response body
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
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
    """
    **Create project parameter from default**

    address to query: **/project/parameter/create/fromdefault**

    Fet json coded dictionary with keys:
    
    - `psid`: access key
    - `uuid`: default parameter uuid

    Posible return status:

    - `201`: project parameter was created
    - `412`: precondition failed, details in response body
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
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
    **List project parameters**

    address to query: **/project/parameter/list**

    Read json coded data as one string with psid
    
    Return json coded list of dictionaries with keys:
    
    - `uuid`: parameter uuid
    - `name`: parameter name
    - `descr`: parameter description
    - `tp`: param type
    - `enum`: Boolean, enumerated value
    - `tecnical`: Boolean, True if parameter is tecnical
    - `values`: posible values of parameter, null if enum is false. List of dictionaries with keys:
       - `value`: one of posible values
       - `caption`: value description
    - `value`: value of parameter, null if there is no one accepted value
    - `caption`: value description, null if `value` is null
    - `votes`: list of dictionaries with keys:
       - `voter`: uuid of voter (participant)
       - `value`: value voted by user
       - `caption`: value description
       - `dt`: dictionary with keys:
          - `year`: year of date
          - `month`: month
          - `day`: day of data
          - `hour`:
          - `minute`:
          - `second`:

    Return status:
    
    - `200`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found with such psid
    - `500`: otherwise
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
    **Change project parameter**

    address to query: **/project/parameter/change**
    
    Get json coded dictionary with keys:
    
    - `psid`: access key
    - `uuid`: parameter uuid
    - `value`: parameter value
    - `caption`: value caption, may be null
    
    Return status:
    
    - `200`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found with such psid
    - `500`: otherwise
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
    **Conform project**

    address to query: **/project/conform**
    
    get json encoded dictionary with keys:
    
    - `psid`:
    - `uuid`: string, parameter uuid

    Return status:
    
    - `201`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found with such psid
    - `500`: otherwise
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

@transaction.commit_on_success
@json_request_handler
def delete_project_route(params):
    """
    get string with psid

    just for testing
    """
    r = validate(_good_string, params)
    if r != None:
        return http.HttpResponse(u'Bad parameter', status=httplib.PRECONDITION_FAILED)
    if Project.objects.filter(participant__psid=params).count() == 0:
        return http.HttpResponse(u'No such project', status=httplib.PRECONDITION_FAILED)
    p = Project.objects.filter(participant__psid=params).all()[0]
    p.delete()
    return http.HttpResponse(u'OK', status=httplib.OK)
