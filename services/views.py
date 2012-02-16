# Create your views here.
# -*- coding: utf-8 -*-

import django.http as http
from django.db import transaction
import json
import httplib
from services.app import execute_create_project, execute_list_projects, execute_list_user_projects, \
    execute_change_project_status, execute_list_default_parameters, execute_create_project_parameter, \
    execute_list_project_parameters, execute_create_project_parameter_from_default, execute_change_participant, \
    execute_invite_participant
from services.common import json_request_handler, getencdec, validate_params, standard_request_handler
from services.models import Project
from svalidate import OrNone, Any, DateTimeString, RegexpMatch, Equal, JsonString
from copy import copy

_good_string = RegexpMatch(r'^[^;:"''|\\/#@&><]*$')
_good_int = RegexpMatch(r'^\d+$')

@transaction.commit_on_success
@standard_request_handler({'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'begin_date' : OrNone(DateTimeString()),
                           'sharing' : Any(*[Equal(a[0]) for a in Project.PROJECT_SHARING]),
                           'ruleset' : Any(*[Equal(a[0]) for a in Project.PROJECT_RULESET]), # fucken amazing !
                           'user_name' : _good_string,
                           'user_id' : OrNone(_good_string),
                           'user_descr' : OrNone(_good_string)})
def create_project_route(prs):
    """
    **Create project**

    address to query **/project/create**

    The body of query must contain dictionary with keys:

    - `name`: name of new project
    - `descr`: description of new project, may be null
    - `begin_date`: hash table with fields:
       - `year`: year of date
       - `month`: month
       - `day`: day of data
       - `hour`:
       - `minute`:
       - `second`:
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
    result, stat = execute_create_project(prs)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(result), status=stat, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'page_number' : OrNone(_good_int),
                           'projects_per_page' : OrNone(_good_int),
                           'status' : OrNone(Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])),
                           'begin_date' : OrNone(DateTimeString()),
                           'search' : OrNone(_good_string)})
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
    pp = copy(pars)
    if pars.get('page_number') != None:
        pp['page_number'] = int(pars['page_number'])
    if pars.get('projects_per_page') != None:
        pp['projects_per_page'] = int(pars['projects_per_page'])
    enc = json.JSONEncoder()
    result = execute_list_projects(pp)
    return http.HttpResponse(enc.encode(result), status=httplib.OK, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'user_id' : _good_string})
def list_user_projects_route(params):
    """
    **List Projects assigned to user**

    address to query: **/project/list/userid**

    Get paramters with names:
    
    - `user_id`: user_id

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
    ret, st = execute_list_user_projects(params['user_id'])
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : '',
                           'status' : Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])})
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
    ret, st = execute_change_project_status(params)
    if st != httplib.OK:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/jsno')

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
    return http.HttpResponse(enc.encode(ret), status=httplib.OK, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'tp' : _good_string,
                           'enum' : JsonString(True),
                           'value' : _good_string,
                           'values' : OrNone(JsonString([{'value' : _good_string,
                                                          'caption' : OrNone(_good_string)}]))})
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
    
    if params['enum'] and (params.get('values') == None):
        return http.HttpResponse(u'if "enum" is true then "values" key must exist', status=httplib.PRECONDITION_FAILED)
    pp = copy(params)
    if params.get('values') != None:
        pp['values'] = dec.decode(params['values']) # decode from json
    pp['enum'] = dec.decode(params['enum'])
    
    ret, stat = execute_create_project_parameter(pp)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type = 'application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
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
    enc = json.JSONEncoder()
    ret, st = execute_create_project_parameter_from_default(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')



@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
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
    ret, st = execute_list_project_parameters(params['psid'])
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'value' : _good_string,
                           'caption' : OrNone(_good_string)})
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
    ret, st = execute_change_project_parameter(params)
    if st != httplib.OK:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
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
    ret, st = execute_conform_project_parameter(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
def delete_project_route(params):
    """
    get string with psid

    just for testing
    """
    if Project.objects.filter(participant__psid=params['psid']).count() == 0:
        return http.HttpResponse(u'No such project', status=httplib.PRECONDITION_FAILED)
    p = Project.objects.filter(participant__psid=params['psid']).all()[0]
    p.delete()
    return http.HttpResponse(u'OK', status=httplib.OK, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'name' : OrNone(_good_string),
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string)})
def change_participant_route(params):
    """
    **Изменить параметры участника проекта**

    Изменяет участника проекта, если участник меняет сам себя либо
    другого участника, которого он пригласил, но тот еще не входил в проект

    адрес: **/participant/change**

    Принимает json словарь с ключами:

    - `psid`: (строка) ключ доступа
    - `uuid`: (строка) ид участника которого будем менять
    - `name`: (строка) новое имя участника либо null
    - `descr`: (строка) описание участника либо null
    - `user_id`: (строка) поле user_id либо null

    Если одно из полей не указано, то не меняет значения этого поля.
    Должно быть указано хотя бы одно поле для изменения name, descr или user_id

    Данных не возвращает в теле

    Статусы возврата:

    - `201`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    if not reduce(lambda a, b: a or b, [params.get(c) != None for c in ['name', 'descr', 'user_id']]):
        return http.HttpResponse(enc.encode(u'At least one of keys "name", "descr", "user_id" must exist'), status=httplib.PRECONDITION_FAILED)

    ret, stat = execute_change_participant(params)
    if ret != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
def list_participants_route(params):
    """
    **Список участников проекта**

    адрес для запроса **/participant/list**

    Принимает json строку с psid

    Возвращает json словарь с ключами:

    - `uuid`: (строка) ид участника
    - `descr`: (строка) описание участника
    - `status`: (строка) один из возможных статусов участника:
       - `accepted`: участник согласован и учавствует в проекте
       - `denied`: участник заерещен для участия в проекте
       - `voted`: участник в процессе согласования
    - `votes`: предложения по участнику, null если `status` != "voted"
       - `voter`: (строка) ид предлагающего
       - `vote`: (строка) одно из возможных предложений
          - `include`: предложение включить в проект
          - `exclude`: предложение исключить из проекта
       - `comment`: (строка) комментарий предложившего
       - `dt`: (словарь с датой) дата время предложения, клдчи:
          - `year`: 
          - `month`:
          - `day`:
          - `hour`:
          - `minute`:
          - `second`:
    
    Статусы возврата:

    - `200`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, stat = execute_list_participants(params['psid'])
    return http.HttpResponse(enc.encode(ret), status=stat)

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string),
                           'comment': OrNone(_good_string)})
def invite_participant_route(params):
    """
    **Пригласить участника**

    путь сервиса **/participant/invite**

    Принимает json словарь с ключами:

    - `psid`: (строка) ключ доступа
    - `name`: (строка) имя участника
    - `descr`: (строка) описание участника, может быть Null
    - `user_id`: (строка) ид пользователя, может быть Null
    - `comment`: (строка) комментарий по предложению, может быть Null
    
    Возвращает json строку с токеном доступа

    Статусы возврата:

    - `201`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, stat = execute_invite_participant(params)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type='application/json')
