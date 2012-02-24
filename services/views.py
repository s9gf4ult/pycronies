# Create your views here.
# -*- coding: utf-8 -*-

import django.http as http
from django.db import transaction
import json
import httplib
from services.app import execute_create_project, execute_list_projects, execute_list_user_projects, \
    execute_change_project_status, execute_list_default_parameters, execute_create_project_parameter, \
    execute_list_project_parameters, execute_create_project_parameter_from_default, execute_change_participant, \
    execute_invite_participant, execute_change_project_parameter, execute_enter_project_open, execute_enter_project_invitation,\
    execute_conform_participant, execute_list_participants, execute_exclude_participant, execute_conform_participant_vote,\
    execute_list_activities
from services.common import json_request_handler, getencdec, validate_params, standard_request_handler
from services.models import Project
from svalidate import OrNone, Any, DateTimeString, RegexpMatch, Equal, JsonString, Able
from copy import copy

_good_string = RegexpMatch(r'^[^;:"''|\\/#&><]*$')

@transaction.commit_on_success
@standard_request_handler({'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'begin_date' : OrNone(DateTimeString()),
                           'sharing' : Any(*[Equal(a[0]) for a in Project.PROJECT_SHARING]),
                           'ruleset' : Any(*[Equal(a[0]) for a in Project.PROJECT_RULESET]), # fucken amazing !
                           'user_name' : _good_string,
                           'user_id' : OrNone(_good_string),
                           'user_descr' : OrNone(_good_string)})
def create_project_route(prs):  # ++TESTED
    """
    **Создать проект**

    путь запроса **/project/create**

    параметры запроса:

    - `name`: имя проекта
    - `descr`: описание проекта, не обязательный
    - `begin_date`: начало проекта. Дата или дата время в ISO формате, не обязательный
    - `sharing`: одно из возможных значений
       - `open`: проект открыт для участия
       - `close`: новых участников добавляет только инициатор
       - `invitation`: новых участников можно приглашать
    - `ruleset`: управление проектом, одно из возможных значений:
       - `despot`: ручное управление
       - `vote`: управление голосованием
       - `auto`: автоуправление
    - `user_name`: имя пользователя
    - `user_id`: строка не обязательный
    - `user_description`: описание пользователя, не обязательный

    возвращает JSON словарь с ключами

    - `uuid` : uuid созданного проекта
    - `psid` : строка доступа для инициатора
    - `token` : токен для волшебной ссылки

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
@standard_request_handler({'page_number' : OrNone(Able(int)),
                           'projects_per_page' : OrNone(Able(int)),
                           'status' : OrNone(Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])),
                           'begin_date' : OrNone(DateTimeString()),
                           'search' : OrNone(_good_string)})
def list_projects_route(pars):  # ++TESTED
    """
    **Список проектов**

    путь запроса: **/project/list**

    Возвращает список открытых для входа проектов в соответствии с параметрами.
    Все параметры не обязательные:

    - `page_number`: номер страницы начиная с 0, если не указан, возвращает нулевую
    - `projects_per_page`: количество проектов на страницу, если не указан возвращает список всех проектов
    - `status`: возвратить только проекты с указанным статусом
       - `opened`: Проект открыт
       - `planning`: Проект на стадии планирования
       - `contractor`: Выбор контрагента
       - `budget`: Формирование бюджета
       - `control`: Контроль
       - `closed`: Закрыт
    - `begin_date`: возвратить только проекты позже этой даты, дата - строка в ISO формате
    - `search`: строка поиска, должна встречаться в имени или описании проекта

    Возвращает JSON словарь с ключами:

    - `pages`: (целое) число страниц при указанном количестве проектов на страницу, если количество проектов
      не указано, возвращает количество проектов вообще, то есть совпадает с длинной списка `projects`
    - `projects` : список словарей с ключами:
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
def list_user_projects_route(params): # ++TESTED
    """
    **Проекты пользователя**

    путь запроса: **/project/list/userid**

    Параметры запроса

    - `user_id`: user_id or token of user, if given token then return just one project

    возвращает JSON список ловарей с ключами

    - `uuid`: uuid проекта
    - `name`: имя проекта
    - `descr`: описание проекта
    - `begin_date`: строка с датой временем начала действия проекта
    - `initiator`: boolean является ли пользователь инициатором этого проекта
    - `status`: статус проекта, строка:
       - `opened`: Проект открыт
       - `planning`: Проект на стадии планирования
       - `contractor`: Выбор контрагента
       - `budget`: Формирование бюджета
       - `control`: Контроль
       - `closed`: Закрыт

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
def change_project_status_route(params): # ++TESTED
    """
    **Изменить статус проекта**

    путь запроса: **/project/status/change**

    Список параметров запроса:

    - `psid`: ключ доступа
    - `status`: статус, один из возможных:
       - `opened`: Проект открыт
       - `planning`: Проект на стадии планирования
       - `contractor`: Выбор контрагента
       - `budget`: Формирование бюджета
       - `control`: Контроль
       - `closed`: Закрыт

    Posible return status:

    - `201`: ok
    - `412`: precondition failed, details in response body (as json)
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
    """
    enc, dec = getencdec()
    ret, st = execute_change_project_status(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/jsno')

@transaction.commit_on_success
def list_default_parameters_route(request): # ++TESTED
    """
    **Просмотр типовых параметров**

    путь запроса: **/parameters/list**

    Возвращает json список словарей с ключами

    - `uuid`: uuid параметра
    - `name`: имя параметра
    - `descr`: описание параметра
    - `tp`: тип параметра
    - `enum`: (boolean) параметр имеет ограниченный набор значений
    - `default`: значение по умолчанию
    - `values`: если `enum` == True тогда это список словарей с ключами
       - `value`: значение
       - `caption`: подпись

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
def create_project_parameter_route(params): # ++TESTED
    """
    **Создать параметр проекта**

    путь запроса **/project/parameter/create**

    Параметры зпроса

    - `psid`: ключ доступа
    - `name`: имя параметра
    - `descr`: описание параметра
    - `tp`: тип параметра
    - `enum`: JSON кодированный boolean (true or false). 'true' если параметр имеет ограниченный набор значений
    - `value`: значение параметра или None если параметр создается без значения
    - `values`: JSON кодированный список словарей с ключами
       - `value`: значение параметра
       - `caption`: подпись

    Posible return status:

    - `201`: project parameter was created
    - `412`: precondition failed, details in response body
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
    """
    enc, dec = getencdec()
    pp = copy(params)
    if params.get('values') != None:
        pp['values'] = dec.decode(params['values']) # decode from json
    pp['enum'] = dec.decode(params['enum'])

    if pp['enum'] and (pp.get('values') == None):
        return http.HttpResponse(u'if "enum" is true then "values" key must exist', status=httplib.PRECONDITION_FAILED)

    ret, stat = execute_create_project_parameter(pp)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type = 'application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
def create_project_parameter_from_default_route(params): # ++TESTED
    """
    **Создать параметр проекта из типового параметра**

    путь запроса: **/project/parameter/create/fromdefault**

    параметры запроса

    - `psid`: ключ доступа
    - `uuid`: uuid типового параметра

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
def list_project_parameters_route(params): # ++TESTED
    """
    **Просмотр списка параметров проекта**

    путь запроса: **/project/parameter/list**

    Параметры запроса:

    - `psid`: ключ доступа

    Возвращает JSON кодированный список словарей с ключами

    - `uuid`: uuid параметра
    - `name`: имя параметра
    - `descr`: описание параметра
    - `tp`: тип параметра
    - `enum`: Boolean, параметр имеет ограниченный набор значений
    - `tecnical`: Boolean, параметр технический
    - `values`: список словарей с ключами. Не указывается если `enum` == false
       - `value`: значение параметра
       - `caption`: подпись
    - `value`: значение параметра
    - `caption`: пояснение значения
    - `votes`: открытые предложения по параметру. список словарей с ключами
       - `voter`: uuid предложившего
       - `value`: предложенное значение
       - `caption`: пояснение значения
       - `dt`: дата время создания предложения, строка в формате ISO

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
def change_project_parameter_route(params): # ++TESTED
    """
    **Изменить параметр проекта**

    путь запроса: **/project/parameter/change**

    Параметры зпроса:

    - `psid`: ключ доступа
    - `uuid`: parameter uuid
    - `value`: parameter value
    - `caption`: value caption, may be null

    Return status:

    - `201`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found with such psid
    - `500`: otherwise
    """
    enc = json.JSONEncoder()
    ret, st = execute_change_project_parameter(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
def conform_project_parameter_route(params): # ++TESTED на прямую не вызывался
    """
    **Согласование проекта**

    путь запроса: **/project/conform**

    Параметры зпроса

    - `psid`: ключ
    - `uuid`: uuid параметра для согласования

    Для управляемого проекта:

       Если пользователь - инициатор: предложенное значение выставляет как текущее, предыдущее текущее значение выставляет как 'changed' все остальные предложения по проекту закрывает со статусом 'denied'. Если не было предложенных значений, то ничего не делает.

       Если пользователь не инициатор: ничего не делает.

    Для остальных типов проекта возвращает статус 501 (временно)

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
def delete_project_route(params): #  FIXME: метод для тестов
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
def change_participant_route(params): # ++TESTED
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
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
def list_participants_route(params): # ++TESTED
    """
    **Список участников проекта**

    адрес для запроса **/participant/list**

    Параметры запроса:

    - `psid`: ключ доступа

    Возвращает список json словарей с ключами:

    - `uuid`: (строка) ид участника
    - `name`: (строка) имя участника
    - `descr`: (строка) описание участника
    - `status`: (строка) один из возможных статусов участника:
       - `accepted`: участник согласован и учавствует в проекте
       - `denied`: участник заерещен для участия в проекте
       - `voted`: статус участника в процессе согласования
    - `votes`: предложения по участнику, null если `status` != "voted"
       - `voter`: (строка) uuid предлагающего
       - `vote`: (строка) одно из возможных предложений
          - `include`: предложение включить в проект
          - `exclude`: предложение исключить из проекта
       - `comment`: (строка) комментарий предложившего
       - `dt`: Дата и время предложения, строка в ISO формате

    Статусы возврата:

    - `200`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, stat = execute_list_participants(params['psid'])
    return http.HttpResponse(enc.encode(ret), status=stat, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string),
                           'comment': OrNone(_good_string)})
def invite_participant_route(params): # ++TESTED
    """
    **Пригласить участника**

    путь сервиса **/participant/invite**

    Принимает json словарь с ключами:

    - `psid`: (строка) ключ доступа
    - `name`: (строка) имя участника
    - `descr`: (строка) описание участника, может быть Null
    - `user_id`: (строка) ид пользователя, может быть Null
    - `comment`: (строка) комментарий по предложению, может быть Null

    Возвращает json словарь с ключами:

    - `token`: (строка) ключ приглашения

    Поведение:

       Если указанный пользователь совпадает с существующим (совпадает имя и
       user_id если последний указан, либо просто имя если не указан user_id),
       то добваляет приглашение на существующего пользователя, иначе создает
       нового пользователя со статусом "voted". Согласование пользователя не
       вызывается.

    Статусы возврата:

    - `201`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, stat = execute_invite_participant(params)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'vote' : Any(Equal('include'), Equal('exclude')),
                           'comment' : OrNone(_good_string)})
def conform_participant_vote_route(params):
    """
    **Подтвердить действие над участником**

    путь запроса: **/participant/vote/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid участника
    - `vote`: "include" или "exclude", подтверждаем приглашение или
      исключение участника соответственно
    - `comment`: комментарий по приглашению, не обязательный
    

    Поведение:

       Если предложение на удаление или включение участника от имени вызывавшего
       сервис уже есть, то согласуем это предложение. Иначе создаем предложение
       и согласуем его.
      
    Статусы возврата:

    - `201`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, st = execute_conform_participant_vote(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')
    

@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string)})
def enter_project_open_route(params): # ++TESTED
    """
    **Вход на открытый проект**

    путь запроса: **/project/enter/open**

    Параметры запроса:

    - `uuid`: ид проекта
    - `name`: имя участника
    - `descr`: описание участника может быть None
    - `user_id`: user_id

    возвращает JSON словарь:

    - `psid`: ключ доступа
    - `token`: токен приглашения

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, st = execute_enter_project_open(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')


@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string,
                           'token' : _good_string})
def enter_project_invitation_route(params): # ++TESTED
    """
    **Вход в проект по приглашению**

    путь запроса: **/project/enter/invitation**

    Параметры запроса:

    - `uuid`: ид проекта
    - `token`: токен приглашения или user_id поле

    Возвращает словарь с одним ключем

    - `psid`: ключ доступа

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, st = execute_enter_project_invitation(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
def conform_participant_route(params): # ++TESTED на прямую не вызывается
    """
    **Согласование участника**

    путь запроса **/participant/conform**

    Параметры запроса:

    - `psid`: (строка) ключ доступа
    - `uuid`: (строка) uuid участника проекта

    Возвращает ничиго

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    r, st = execute_conform_participant(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(r), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'comment' : OrNone(_good_string)})
def exclude_participant_route(params):
    """
    **Исключить участника**

    путь запроса: **/participant/exclude**

    Параметры запроса:

    - `psid`: (строка) ключ доступа
    - `uuid`: (строка) идентификатор участника
    - `comment`: (строка) комментарий, не обязательный

    В теле ответа ниче нету

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, st = execute_exclude_participant(params)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
def list_activities_route(params):
    """
    **Просмотр мероприятий проекта**

    путь запроса: **/activity/list**

    Параметры запроса:

    - `psid`: (строка) код доступа

    Возвращает JSON список словарей с ключами:

    - `uuid`: uuid мероприятия
    - `name`: имя мероприятия
    - `descr`: описание мероприятия
    - `begin`: строка с датой временем в ISO формате - дата время начала мероприятия, может быть пустым
    - `end`: строка с датой временем в ISO формате - дата время окончания мероприятия, может быть пустым
    - `status`: стрка со статусом мероприятия, может быть одно из:
       - `created`: Мероприятие создано
       - `voted`: Мероприятие предложено для добавления
       - `accepted`: Мероприятие используется в проекте
       - `denied`: Мероприятие исключено
    - `votes`: предложения по мероприятию, список словарей с ключами:
       - `uuid`: uuid участника проекта
       - `vote`: предложение, одно из возможных значений:
          - `include`: голос за то чтобы мероприятие было включено в проект
          - `exclude`: голос за исключение мероприятия из проекта
       - `comment`: комментарий голосовавшего
       - `dt`: дата время в ISO формате, время голосования участника
    - `participant`: (bool) является ли участник (по psid) участником данного мероприятия

    Поведение:

       Если статус мероприятия "accepted", "denied" или "voted" то мероприятие
       показывается всем участникам. Если статус == "created" то мероприятие
       будет показано только тому пользователю, который его создал.

    Статусы возврата:

    - `200`: ok
    - `404`: не верный psid, нет такого пользователя
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    ret, st = execute_list_activities(params['psid'])
    if st != httplib.OK:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')
