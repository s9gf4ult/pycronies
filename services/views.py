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
    execute_list_activities, execute_activity_participation, execute_create_activity, execute_public_activity, execute_conform_project_parameter, \
    execute_activity_list_participants, execute_activity_delete, execute_conform_activity, execute_activity_deny, \
    execute_create_activity_parameter, execute_create_activity_parameter_from_default,\
    execute_change_activity_parameter, execute_conform_activity_parameter, execute_list_activity_parameters, \
    execute_create_project_resource, execute_include_personal_resource, execute_list_activity_resources, \
    execute_create_project_resource, execute_include_activity_resource, execute_exclude_activity_resource, \
    execute_conform_activity_resource, execute_create_resource_parameter, execute_create_resource_parameter_from_default, \
    execute_list_activity_resource_parameters, execute_change_resource_parameter, execute_conform_resource_parameter

from services.common import getencdec, standard_request_handler, typical_json_responder
from services.models import Project, Resource
from services.statuses import PARAMETERS_BROKEN
from svalidate import OrNone, Any, DateTimeString, RegexpMatch, Equal, JsonString, Able, Validate
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
@typical_json_responder(execute_create_project, httplib.CREATED)
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
    pass

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
       - `end_date`: дата время окончания проекта строка в ISO формате
       - `participants`: количество участников в проекте

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

    Поведение:

       Если не найден ни один пользователь с указанным user_id или токеном,
       возвращаем пустой список

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
                           'status' : Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS]),
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_change_project_status, httplib.CREATED)
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
    - `comment`: комментарий пользователя

    Posible return status:

    - `201`: ok
    - `412`: precondition failed, details in response body (as json)
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
    """
    pass

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
                           # 'values' : OrNone(JsonString([{'value' : _good_string,
                           #                                'caption' : OrNone(_good_string)}])),
                           'caption' : OrNone(_good_string),
                           'comment' : OrNone(_good_string)})
def create_project_parameter_route(params): # ++TESTED
    """
    **Создать параметр проекта**

    путь запроса **/project/parameter/create**

    Параметры зпроса

    - `psid`: ключ доступа
    - `name`: имя параметра
    - `descr`: описание параметра, не обязательно
    - `tp`: тип параметра
    - `enum`: JSON кодированный boolean (true or false). 'true' если параметр имеет ограниченный набор значений
    - `value`: значение параметра или None если параметр создается без значения
    - `values`: JSON кодированный список словарей с ключами
       - `value`: значение параметра
       - `caption`: подпись
    - `caption`: пояснение к значению
    - `comment`: комментарий пользователя

    Posible return status:

    - `201`: project parameter was created
    - `412`: precondition failed, details in response body
    - `404`: user was not found
    - `501`: query was not post
    - `500`: otherwise
    """
    enc, dec = getencdec()
    pp = copy(params)
    pp['enum'] = dec.decode(params['enum'])
    if pp['enum']:
        v = Validate()
        r = v.validate(JsonString([{'value' : _good_string,
                                    'caption' : OrNone(_good_string)}]),
                       pp.get('values'))
        if r != None:
            return http.HttpResponse(enc.encode({'code' : PARAMETERS_BROKEN,
                                                 'error' : r,
                                                 'caption' : 'You must give valid "values" if "enum" is true'}),
                                     status = httplib.PRECONDITION_FAILED,
                                     content_type = 'application/json')
        pp['values'] = dec.decode(pp['values'])

    ret, stat = execute_create_project_parameter(pp)
    if stat != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=stat, content_type = 'application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_create_project_parameter_from_default, httplib.CREATED)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
@typical_json_responder(execute_list_project_parameters, httplib.OK)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'value' : _good_string,
                           'caption' : OrNone(_good_string),
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_change_project_parameter, httplib.CREATED)
def change_project_parameter_route(params): # ++TESTED
    """
    **Изменить параметр проекта**

    путь запроса: **/project/parameter/change**

    Параметры зпроса:

    - `psid`: ключ доступа
    - `uuid`: parameter uuid
    - `value`: parameter value
    - `caption`: value caption, may be null
    - `comment`: users's comment

    Return status:

    - `201`: ok
    - `412`: precondition failed, details in response body
    - `404`: user was not found with such psid
    - `500`: otherwise
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_conform_project_parameter, httplib.CREATED)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
def delete_project_route(params): #  FIXME: метод для тестов
    """
    get string with psid

    just for testing
    """
    from django.conf import settings
    if not settings.DEBUG:
        return http.HttpResponse('Works just in debug mode', status=httplib.INTERNAL_SERVER_ERROR)
    if Project.objects.filter(participant__psid=params['psid']).count() == 0:
        return http.HttpResponse(u'No such project', status=httplib.PRECONDITION_FAILED)
    p = Project.objects.filter(participant__psid=params['psid']).all()[0]
    p.delete()
    return http.HttpResponse(u'OK', status=httplib.OK, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : OrNone(_good_string),
                           'name' : OrNone(_good_string),
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string)})
def change_participant_route(params): # ++TESTED
    """
    **Изменить параметры участника проекта**

    Изменяет участника проекта, если участник меняет сам себя либо
    другого участника, которого он пригласил, но тот еще не входил в проект

    адрес: **/participant/change**

    Парметры запросаи:

    - `psid`: (строка) ключ доступа
    - `uuid`: (строка) ид участника которого будем менять, не обязательный параметр
      если не указано, то меняем сами себя
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
@typical_json_responder(execute_list_participants, httplib.OK)
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
    - `votes`: предложения по участнику
       - `voter`: (строка) uuid предлагающего
       - `vote`: (строка) одно из возможных предложений
          - `include`: предложение включить в проект
          - `exclude`: предложение исключить из проекта
       - `comment`: (строка) комментарий предложившего
       - `dt`: Дата и время предложения, строка в ISO формате
    - `me`: Bool признак того что этот пользователь - и есть мы


    Статусы возврата:

    - `200`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string),
                           'comment': OrNone(_good_string)})
@typical_json_responder(execute_invite_participant, httplib.CREATED)
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
       нового пользователя со статусом 'voted'. Согласование пользователя не
       вызывается.

    Статусы возврата:

    - `201`: ok
    - `404`: psid не найден
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'vote' : Any(Equal('include'), Equal('exclude')),
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_conform_participant_vote, httplib.CREATED)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'user_id' : OrNone(_good_string)})
@typical_json_responder(execute_enter_project_open, httplib.CREATED)
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
    pass


@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string,
                           'token' : _good_string})
@typical_json_responder(execute_enter_project_invitation, httplib.CREATED)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_conform_participant, httplib.CREATED)
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
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : OrNone(_good_string),
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_exclude_participant, httplib.CREATED)
def exclude_participant_route(params):
    """
    **Исключить участника**

    путь запроса: **/participant/exclude**

    Параметры запроса:

    - `psid`: (строка) ключ доступа
    - `uuid`: (строка) идентификатор участника, не обязательный,
      если не указан, подразумевается удаление самого себя из проекта
    - `comment`: (строка) комментарий, не обязательный

    В теле ответа ниче нету

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип проекта != управляемый, временно
    - `500`: ошибка сервера
    """

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
@typical_json_responder(execute_list_activities, httplib.OK)
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
    - `votes`: предложения по мероприятию, может быть None, список словарей с ключами:
       - `uuid`: uuid участника проекта
       - `vote`: предложение, одно из возможных значений:
          - `include`: голос за то чтобы мероприятие было включено в проект
          - `exclude`: голос за исключение мероприятия из проекта
       - `comment`: комментарий голосовавшего
       - `dt`: дата время в ISO формате, время голосования участника
    - `participant`: (bool) является ли участник (по psid) участником данного мероприятия

    Поведение:

       Если статус мероприятия 'accepted', 'denied' или 'voted' то мероприятие
       показывается всем участникам. Если статус == 'created' то мероприятие
       будет показано только тому пользователю, который его создал.

    Статусы возврата:

    - `200`: ok
    - `404`: не верный psid, нет такого пользователя
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'action' : Any(Equal('include'), Equal('exclude')),
                           'uuid' : _good_string,
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_activity_participation, httplib.CREATED)
def activity_participation_route(params):
    """
    **Участие в мероприятии**

    путь запроса: **/activity/participation**

    Параметры запроса:

    - `psid`: (строка) ключ запроса
    - `action`: 'include' or 'exclude', действие: включить участника в мероприятие или исключить
    - `uuid`: ид мероприятия
    - `comment`: комментарий участия в мероприятии, не обязательный

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'begin' : DateTimeString(),
                           'end' : DateTimeString()})
@typical_json_responder(execute_create_activity, httplib.CREATED)
def create_activity_route(params):
    """
    **Создание мероприятия**

    путь запроса: **/activity/create**

    Параметры запроса:

    - `psid`: ключ доступа
    - `name`: имя мероприятия
    - `descr`: описание мероприятия
    - `begin`: дата время в ISO формате - строка
    - `end`: дата время в ISO формате - строка

    Возвращает JSON словарь:

    - `uuid`: ид нового мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если тип управления проектом не 'despot' (временно)
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_public_activity, httplib.CREATED)
def public_activity_route(params):
    """
    **Публикация мероприятия**

    путь запроса: **/activity/public**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия
    - `comment`: комментарий, не обязательный параметр

    Поведение:

       Если мероприятие имеет статус 'created' и создано оно участником, то
       меняем статус на 'voted', далее предлагаем мероприятие на добавление и
       вызываем согласование мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_activity_delete, httplib.CREATED)
def activity_delete_route(params):
    """
    **Удаление мероприятия**

    путь запроса: **/activity/delete**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия

    Поведение:

       Если пользователь - создатель мероприятия и статус мероприятия ==
       'created' то удаляем мероприятие

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_activity_deny, httplib.CREATED)
def activity_deny_route(params):
    """
    **Исключение мероприятия**

    путь запроса: **/activity/deny**

    Параметры запроса:

    - `psid`: строка доступа
    - `uuid`: ид мероприятия
    - `comment`: коментарий участника

    Поведение:

       Создаем предложение на удаление мероприятия (если такого еще нет) и
       вызываем согласование мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_activity_list_participants, httplib.OK)
def list_activity_participants_route(params):
    """
    **Просмотр списка участников**

    путь запроса: **/activity/participant/list**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid мероприятия

    Возвращает JSON список строк с UUID участников проекта, учавствующих в
    данном мероприятии

    Поведение:
    
    Если мероприятие в данный момент не активно, возвращает пустой список

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_conform_activity, httplib.CREATED)
def conform_activity_route(params):
    """
    **Согласование мероприятия**

    путь запроса: **/activity/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass

# @transaction.commit_on_success
# @standard_request_handler({'psid' : _good_string})
# @typical_j

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'tp' : _good_string,
                           'enum' : JsonString(True),
                           'value' : OrNone(_good_string)})
def create_activity_parameter_route(params):
    """
    **Создание параметра мероприятия**

    путь запроса: **/activity/parameter/create**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия
    - `name`: имя параметра мероприятия
    - `descr`: описание параметра, не обязательный
    - `tp`: тип параметра
    - `enum`: JSON кодированное значение True или False, означает
      что параметр имеет ограниченный набор значений
    - `value`: Значение параметра при создании, может быть Null
    - `values`: JSON кодированный список словарей с ключами:
       - `value`: значение параметра (одно из возможных в списке)
       - `caption`: описание значения, может быть Null

    Возвращает JSON кодированный словарь:

    - `uuid`: ид нового параметра

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    enc, dec = getencdec()
    pp = copy(params)
    pp['enum'] = dec.decode(pp['enum'])
    if pp['enum']:
        v = Validate()
        r = v.validate({'values' : JsonString([{'value' : _good_string,
                                                'caption' : OrNone(_good_string)}])},
                       pp)
        if r != None:
            return http.HttpResponse(enc.encode({'code' : PARAMETERS_BROKEN,
                                                 'error' : r,
                                                 'caption' : 'values are broken'}),
                                     status = httplib.PRECONDITION_FAILED,
                                     content_type='application/json')
        pp['values'] = dec.decode(pp['values'])
    ret, st = execute_create_activity_parameter(pp)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'default' : _good_string})
@typical_json_responder(execute_create_activity_parameter_from_default, httplib.CREATED)
def create_activity_parameter_from_default_route(params):
    """
    **Содание параметра мероприятия из типового**

    путь запроса: **/activity/parameter/create/fromdefault**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid мероприятия
    - `default`: uuid типового параметра

    Возвращает JSON словарь:

    - `uuid`: uuid нового параметра мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_list_activity_parameters, httplib.OK)
def list_activity_parameters_route(params):
    """
    **Получение перечня параметров мероприятия**

    путь запроса: **/activity/parameter/list**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия

    Возвращает JSON кодированный список словарей с ключами:

    - `uuid`: ид параметра
    - `name`: имя параметра
    - `descr`: описание параметра
    - `tp`: тип параметра
    - `enum`: Boolean, является ли параметр параметром с
      ограниченным набором значений
    - `values`: список словарей с ключами:
       - `value`: значение
       - `caption`: описание
    - `value`: значение параметра, если нет значений то None
    - `caption`: описание значения, если `value` == None то None
    - `votes`: список словарей с ключами:
       - `uuid`: uuid участника проекта, голосовавшего за параметр
       - `value`: значение, которое предложил участник
       - `caption`: описание значения
       - `comment`: комментарий участника
       - `dt`: дата время в ISO формате (строка), время голосования участника

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'value' : _good_string,
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_change_activity_parameter, httplib.CREATED)
def change_activity_parameter_route(params):
    """
    **Изененеие параметра мероирятия**

    путь запроса: **/activity/parameter/change**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид параметра мероприятия
    - `value`: новое предлагаемое значение
    - `comment`: комментарий по изменению, может быть Null

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_conform_activity_parameter, httplib.CREATED)
def conform_activity_parameter_route(params):
    """
    **Согласовать параметр проекта**

    путь запроса: **/activity/parameter/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид параметра мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'activity': _good_string,
                           'amount' : Able(float)})
def include_personal_resource_route(params):
    """
    **Добавление/удаление личного ресурса**

    путь запроса: **/participant/resource/use**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид ресурса
    - `activity`: uuid мероприятия
    - `amount`: количество ресурса, Float строкой

    Поведение:

       Если количество ресурса указано меньше чем 0.001
       то ресурс исключается из личного использования
       участником. Чтобы добавить ресурс снова, нужно
       вызывать этот метод и указать колчиество большее
       чем 0.001

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    enc = json.JSONEncoder()
    prms = copy(params)
    prms['amount'] = float(prms['amount'])
    ret, st = execute_include_personal_resource(prms)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : OrNone(_good_string)})
@typical_json_responder(execute_list_activity_resources, httplib.OK)
def list_activity_resources_route(params):
    """
    **Просмотр ресурсов на мероприятии**

    путь запроса: **/activity/resource/list**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: не обязательный uuid мероприятия, если не указан, то
      вернет все ресурсы проекта

    Возвращает в тебе ответа JSON кодирванный список словарей
    с ключами:

    - `uuid`: uuid ресурса
    - `name`: имя ресурса
    - `product`: ид продукта    #  FIXME: добавить
    - `descr`: описание ресурса
    - `units`: еденица измерения (строка с названием)
    - `status`: статус ресурса на мероприятии
       - `accepted`: может использоваться участником или уже используется
         на мероприятии
       - `voted`: предложен для использования
    - `use`: использование ресурса, одно из возможных значений
       - `personal`: ресурс может быть использован как личный ресурс
       - `common`: ресерс используется только как общий ресурс
    - `site`: принадлежность ресурса, одно из возможных значений
       - `internal`: Внутренний ресурс, не требуется поставка
       - `external`: Внешний ресурс, нужна покупка
    - `votes`: предложения по ресурсу, JSON список словарей
       - `uuid`: ид участника проекта, выдвинувшего предложение
       - `vote`: предложенное действие, одно из возможных значений
          - `include`: включить ресурс в мероприятие
          - `exclude`: исключить ресурс из мероприятия
       - `comment`: комментарий участника
       - `dt`: дата создания предложения
    - `contractors`: список поставщиков, содержит пустой список
      если просматриваем список ресурсов по мероприятию а не по проекту #  FIXME: добавить
       - `name`: имя поставщика
       - `user`: user_id поставщика
       - `cost`: предложенная цена по ресурсу
       - `amount`: количетсво ресурса, согласованное для поставки данным поставщиком
       - `offer_amount`: количество ресурса, которое поставщик может поаставить
       - `votes`: предложения по этому поставщику
          - `uuid`: uuid пользователя
          - `amount`: количество ресурса предложенное участником проекта
            для поставки данным поставщиком. То есть сколько ресурса взять
            у данного поставщика.
    - `used`: Boolean, признак того, что ресурс используется
      на этом мероприятии
    - `amount`: количество ресурса, Float строкой
    - `cost`: цена, если выбран поставщик, не возвращается для просмотра по
      мероприятию, ибо не однозначно количество ресурса, которое надо отобразить #  FIXME: добавить

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'units' : _good_string,
                           'use' : Any(*[Equal(a[0]) for a in Resource.RESOURCE_USAGE]),
                           'site' : Any(*[Equal(a[0]) for a in Resource.RESOURCE_SITE])})
@typical_json_responder(execute_create_project_resource, httplib.CREATED)
def create_project_resource_route(params):
    """
    **Создать ресурс в проекте**

    путь запроса: **/resource/create**

    Параметры запроса:

    - `psid`: ключ доступа
    - `name`: имя ресурска
    - `descr`: описание ресурса
    - `units`: название еденицы измерения
    - `use`: использование ресурса, одно из возможных значений
       - `personal`: ресурс может быть использован как личный ресурс
       - `common`: ресерс используется только как общий ресурс
    - `site`: принадлежность ресурса, одно из возможных значений
       - `internal`: Внутренний ресурс, не требуется поставка
       - `external`: Внешний ресурс, нужна покупка

    Возвращает JSON кодированный словарь

    - `uuid`: ид нового ресурса

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера

    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'activity' : _good_string,
                           'need' : OrNone(JsonString(True)),
                           'amount' : OrNone(Able(float)),
                           'comment' : OrNone(_good_string)})
def include_activity_resource_route(params):
    """
    **Добавление ресурса мероприятия**

    путь запроса: **/activity/resource/include**

    Параметры запроса:

    - `psid`: строка доступа
    - `uuid`: ид ресурса
    - `activity`: uuid мероприятия
    - `need`: не обязательный JSON кодированный Boolean, признак того, что на мероприятии этот ресурс необходим и без
      него мероприятие не может быть запущено, если ресурс - личный, то этот параметр игнорируется
    - `amount`: не обязательное количество ресурса, Float строкой. Если ресурс личный - то игнорируется
    - `comment`: не обязательный комментарий

    Поведение:

       Повторно добавление ресурсов заерещено

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    enc, dec = getencdec()
    prms = copy(params)
    if prms.get('need') != None:
        prms['need'] = dec.decode(prms['need'])
    if prms.get('amount') != None:
        prms['amount'] = float(prms['amount'])
    ret, st = execute_include_activity_resource(prms)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type='application/json')

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'activity' : _good_string,
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_exclude_activity_resource, httplib.CREATED)
def exclude_activity_resource_route(params):
    """
    **Исключить ресурс из мероприятия**

    путь запроса: **/activity/resource/exclude**

    Параметры зпароса:

    - `psid`: ключ доступа
    - `uuid`: uuid ресурса
    - `activity`: uuid мероприятия
    - `comment`: не обязательный комментарий участника

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({})
@typical_json_responder(execute_conform_activity_resource, httplib.CREATED)
def conform_activity_resource_route(params):
    """
    **Согласование ресурса мероприятия**

    путь запроса: **/activiry/resource/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid ресурса
    - `activity`: uuid мероприятия

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'activity' : _good_string,
                           'uuid' : _good_string,
                           'name' : _good_string,
                           'descr' : OrNone(_good_string),
                           'tp' : _good_string,
                           'enum' : JsonString(True),
                           'value' : OrNone(_good_string)})
                           # 'values' : OrNone([{'value' : _good_string,
                           #                     'caption' : OrNone(_good_string)}])})
def create_activity_resource_parameter_route(params):
    """
    **Добавить праметр ресурса мероприятия**

    путь запроса: **/activity/resource/parameter/create**

    Параметры запроса:

    - `psid`: ключ доступа
    - `activity`: ид мероприятия
    - `uuid`: ид ресурса
    - `name`: имя параметра ресурса
    - `descr`: не обязательное описание параметра
    - `tp`: тип ресурса
    - `enum`: JSON кодированный Boolean, параметр имеет ограниченный набор значений
    - `value`: не обязательное значение параметра (если пусто то параметра не существует)
    - `values`: не обязательный набор возможных значений, JSON список словарей с ключами
       - `value`:
       - `caption`: не обязательный параметр

    Возвращает JSON кодированный словарь

    - `uuid`: ид параметр ресурса

    Поведение:

       Если ресурс - личный, то создает параметр личного использования видный
       только тому кто его создал, если ресурс общий, то создается общий
       параметр использования для мероприятия видный и изменяемый всеми

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    enc, dec = getencdec()
    pp = copy(params)
    pp['enum'] = dec.decode(pp['enum'])
    if pp['enum']:
        v = Validate()
        r = v.validate(JsonString([{'value' : _good_string,
                                    'caption' : OrNone(_good_string)}]),
                       pp['values'])
        if r != None:
            return http.HttpResponse(enc.encode({ 'code' : PARAMETERS_BROKEN,
                                                  'error' : r,
                                                  'caption' : 'You must give proper "values" if "enum" field is true'}),
                                     status = httplib.PRECONDITION_FAILED,
                                     content_type='application/json')
        pp['values'] = dec.decode(pp['values'])
    ret, st = execute_create_resource_parameter(pp)
    if st != httplib.CREATED:
        transaction.rollback()
    return http.HttpResponse(enc.encode(ret), status=st, content_type = 'application/json')


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'activity' : _good_string,
                           'uuid' : _good_string,
                           'default' : _good_string})
@typical_json_responder(execute_create_resource_parameter_from_default, httplib.CREATED)
def create_activity_resource_parameter_from_default_route(params):
    """
    **Добавить типовой параметр ресурса**

    путь запроса: **/ativity/resource/parameter/create/from_default**

    Параметры запроса:

    - `psid`: ключ доступа
    - `activity`: ид мероприятия
    - `uuid`: ид ресурса
    - `default`: ид типового ресурса

    Возвращает JSON словарь:

    - `uuid`: ид параметра ресурса

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != 'despot'
    - `500`: ошибка сервера
    """
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'activity' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_list_activity_resource_parameters, httplib.OK)
def list_activity_resource_parameters_route(params):
    """
    **Просмотр перечня параметров ресурса**

    путь запроса: **/activity/resource/parameter/list**

    Параметры запроса:

    - `psid`: ключ доступа
    - `activity`: ид мероприятия
    - `uuid`: ид ресурса

    Возвращает JSON список словарей

    - `uuid`: uuid параметра ресурса
    - `name`: имя ресурса
    - `descr`: описание ресурса
    - `tp`: тип ресурса
    - `enum`: Boolean, параметр имеет ограниченный набор значений
    - `values`: список возможных значений в виде списка словарей
       - `value`: значение
       - `caption`: описание
    - `value`: значение параметра
    - `caption`: описание значения, если нет занчения то тоже пустой
    - `votes`: список предложений по параметру, список словарей:
       - `uuid`: uuid предложившего участника
       - `value`: предложенное значение параметра
       - `caption`: описание параметра
       - `comment`: комментарий предложившего
       - `dt`: дата время предложения

    Поведение:

       Если ресурс личный - то взарвщает список параметро личного использования,
       если ресурс общий то параметры использования в мероприятии

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'value' : _good_string,
                           'caption' : OrNone(_good_string),
                           'comment' : OrNone(_good_string)})
@typical_json_responder(execute_change_resource_parameter, httplib.CREATED)
def change_resource_parameter_route(params):
    """
    **Изменить значение параметра ресурса**

    путь запроса: **/activity/resource/parameter/change**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid параметра ресурса
    - `value`: новое значение
    - `caption`: не обязательное пояснение для значения
    - `comment`: комментарий пользователя

    Поведение:

       Изменяет параметр личного использования в том случае если ресурс -
       личный, этот параметр не будет никому виден кроме того кто его создавал и
       менял. Если ресурс - общий, то изменяется параметр использования на
       мероприятии, это измененеие будет видно всем

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass



@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string})
@typical_json_responder(execute_conform_resource_parameter, httplib.CREATED)
def conform_resource_parameter_route(params):
    """
    **Согласование параметра ресурса**

    путь запроса: **/activity/resource/parameter/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: ид параметра ресурса мероприяти

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера

    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'resource' : _good_string,
                           'contractor' : _good_string,
                           'amount' : OrNone(Able(float))})
@typical_json_responder(execute_use_contractor, httplib.CREATED)
def use_contractor_route(params): #  FIXME: implement
    """
    **Воспользоваться предложением поставщика**

    путь запроса: **/resource/contractor/use**

    Параметры запроса

    - `psid`: ключ доступа
    - `resource` : uuid ресурса
    - `contractor`: user_id поставщика
    - `amount`: не обязательный параметр количества ресурса, которое
      будет взято у этого поставщика если не указано, то будет взято все
      свободное количество ресурса которое еще не поставляется ни одним
      поставщиком на проекте, Если указан 0, то использование поставщика
      снимается
    """
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string})
@typical_json_responder(execute_report_project_statistics, httplib.OK)
def project_statistics_route(params): #  FIXME: заимплементить
    """
    **Отчет о пректе**

    путь запроса: **/report/project**

    Параметры запроса:

    - `psid`: ключ доступа к проекту

    Вовзращает JSON словарь с ключами:

    - `uuid`: ид проекта
    - `name`: имя проекта
    - `descr`: описание проекта
    - `sharing`: строка, описывает политику добавления новых участников проекта
       - `open`: проект открыт для свободного доступа
       - `invitation`: проект доступен для входа по приглашениям
       - `close`: доступом в проект упаравляет инициатор
    - `ruleset`: политика управления свойствами проекта
       - `despot`: всем управляет инициатор
       - `auto`: авто управление
       - `vote`: управление голосованием
    - `begin_date`: дата старта проекта
    - `end_date`: дата завершения проекта
    - `resources`: описывает ресурсы задействованные на проекте,
      то есть только те ресурсы, которые используются хотя бы одним мероприятием
      или участником мероприятия, в количестве более 0.001. Является списком хэш
      таблиц с ключами:
       - `uuid`: uuid ресурса
       - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
       - `amount`: суммарное количество ресурса использованное на проекте
       - `cost`: цена ресурса, если есть поставщик, None если поставщика нет
       - `name`: имя ресурса
       - `descr`: описание ресурса
       - `units' : название еденицы измерения ресурса
       - `use` : способ использования ресурса, одно из возможных значений:
          - `common`: общий ресурс для мероприятия
          - `personal`: ресурс персональный
       - `site`: принадлежность ресурса, строка, одно из возможных значений
          - `internal`: ресурс внутренний, покупать не нужно
          - `external`: ресурс нужно еще приобрести

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера

    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuids' : OrNone(JsonString([_good_string]))})
@typical_json_responder(execute_activity_statistics, httplib.OK)
def activity_statistics_route(params):  #  FIXME: заимплементить
    """
    **Отчет по мероприятию / мероприятиям**

    путь запроса: **/report/activity**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuids`: не обязательный JSON список uuid мероприятий для получения
      отчета только по выбранным мероприятиям, если не указан или пустой,
      то возвращается отчет по всем мероприятиям выбранного проекта

    Возвращает JSON кодированный спимок словарей с ключами:

    - `uuid`: ид мероприятия
    - `name`: имя мероприятия
    - `descr`: описание мероприятия
    - `begin`: дата начала мероприятия ISO строка
    - `end`: дата окончания мероприятия ISO дата строкой
    - `resources`: ресурсы мероприятия и личные ресрусы которые используются на этом мероприятии,
      список словарей с ключами:
       - `uuid`: uuid ресурса
       - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
       - `amount`: суммарное количество ресурса использованное на мероприятии
       - `name`: имя ресурса
       - `descr`: описание ресурса
       - `units' : название еденицы измерения ресурса
       - `use` : способ использования ресурса, одно из возможных значений:
          - `common`: общий ресурс для мероприятия
          - `personal`: ресурс персональный
       - `site`: принадлежность ресурса, строка, одно из возможных значений
          - `internal`: ресурс внутренний, покупать не нужно
          - `external`: ресурс нужно еще приобрести
    - `participants`: участники этого мероприятия, список словарей
       - `uuid`: ид пользователя
       - `create`: дата входа пользователя на проект, ISO строка
       - `login`: дата последнего логина пользователя, ISO строка
       - `is_initiator`: Boolean является ли пользователель инициатором
       - `user`: user_id пользователя
       - `name`: имя (ник) пользователя
       - `descr`: описание пользователя
       - `resources`: ресурсы мероприятия и личные ресрусы которые используются на этом мероприятии,
         список словарей с ключами:
          - `uuid`: uuid ресурса
          - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
          - `amount`: суммарное количество ресурса использованное данным участником,
            на данном мероприятии, персональные ресурсы передаются как есть, для
            общих ресурсов вычисляется amount / count(participants), то есть
            количество ресурса деленное на количество участников в этом
            мероприятии
          - `cost`: цена ресурса, если есть поставщик, None если поставщика нет
          - `name`: имя ресурса
          - `descr`: описание ресурса
          - `units' : название еденицы измерения ресурса
          - `use` : способ использования ресурса, одно из возможных значений:
             - `common`: общий ресурс для мероприятия
             - `personal`: ресурс персональный
          - `site`: принадлежность ресурса, строка, одно из возможных значений
             - `internal`: ресурс внутренний, покупать не нужно
             - `external`: ресурс нужно еще приобрести

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера

    """
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuids' : OrNone(JsonString([_good_string]))})
@typical_json_responder(execute_participant_statistics, httplib.OK)
def participant_statistics_route(params): #  FIXME: заимплементить
    """
    **Отчет по пользователю / пользователям**

    путь запроса: **/report/participant**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuids`: JSON список uuid пользователей, если не указан или пустой,
      возвращается отчет по всем пользователям

    Возвращет JSON список словарей с ключами:

    - `uuid`: ид пользователя
    - `create`: дата входа пользователя на проект, ISO строка
    - `login`: дата последнего логина пользователя, ISO строка
    - `is_initiator`: Boolean является ли пользователель инициатором
    - `user`: user_id пользователя
    - `name`: имя (ник) пользователя
    - `descr`: описание пользователя
    - `resources`: ресурсы мероприятия и личные ресрусы которые используются на этом мероприятии,
      список словарей с ключами:
       - `uuid`: uuid ресурса
       - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
       - `amount`: суммарное количество ресурса использованное данным участником,
         персональные ресурсы просто складываются, тогда как для общих ресурсов
         вычисляется среднее значение количества ресурса использованное данным
         участником на данном мероприятии. Например пользователь учавствует в 2х
         мероприятиях, в одном мероприятии 10 участников во втором 15, в первом
         мероприятии используется ресурс А в поличестве 100, на втором
         используется ресурс Б в количетсве 30, тогда ресурс А используется
         каждым участником мероприятия в количестве 100 / 10 = 10, а ресурс Б
         30 / 15 = 2. Потому что каждый участник в равной степени использует общий
         ресурс каждого мероприятия
       - `cost`: цена ресурса, если есть поставщик, None если поставщика нет
       - `name`: имя ресурса
       - `descr`: описание ресурса
       - `units' : название еденицы измерения ресурса
       - `use` : способ использования ресурса, одно из возможных значений:
          - `common`: общий ресурс для мероприятия
          - `personal`: ресурс персональный
       - `site`: принадлежность ресурса, строка, одно из возможных значений
          - `internal`: ресурс внутренний, покупать не нужно
          - `external`: ресурс нужно еще приобрести

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера

    """
    pass

@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string})
@typical_json_responder(execute_contractor_list_project_resources, httplib.OK)
def contractor_list_project_resources_route(params): #  FIXME: implement
    """
    **Просмотр ресурсов проекта для поставщика**

    путь запроса: **/contractor/project/resource/list**

    Параметры запроса:

    - `uuid`: ид проекта для просмотра ресурсов

    Результат JSON список словарей

    - `uuid`: uuid ресурса
    - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
    - `amount`: суммарное количество ресурса использованное на проекте
    - `free_amount`: количевто ресурса доступное для предложения
    - `name`: имя ресурса
    - `descr`: описание ресурса
    - `units' : название еденицы измерения ресурса
    - `use` : способ использования ресурса, одно из возможных значений:
       - `common`: общий ресурс для мероприятия
       - `personal`: ресурс персональный
    - `site`: принадлежность ресурса, строка, одно из возможных значений
       - `internal`: ресурс внутренний, покупать не нужно
       - `external`: ресурс нужно еще приобрести

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'user' : _good_string,
                           'uuid' : _good_string,
                           'cost' : Able(float),
                           'amount' : OrNone(Able(float))})
@typical_json_responder(execute_contractor_offer_resource, httplib.CREATED)
def contractor_offer_resource_route(params): #  FIXME: implement
    """
    **Предложение цены на проекте для поставщика**

    путь запроса: **/contractor/resource/offer**

    Параметры запроса:

    - `user`: user_id поставщика
    - `uuid`: ид ресурса
    - `cost`: предложенная цена за еденицу ресурса
    - `amount`: не обязательное количество ресурса которое поставщик может предложить.
      Если не указано, то считается что поставщик может поставить любое количество
      необходимого ресурса, Если указано количество 0, то предложение снимается.

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'user' : _good_string,
                           'name' : _good_string,
                           'contacts' : OrNone(JsonString([{'type' : _good_string,
                                                            'value' : _good_string}]))})
@typical_json_responder(execute_create_contractor, httplib.CREATED)
def create_contractor_route(params):    #  FIXME: implement
    """
    **Создание поставщика**

    путь запроса: **/contractor/create**

    Параметры запроса

    - `user`: user_id поставщика
    - `name`: имя поствщика
    - `contacts`: не обязательный параметр контакты поставщика,
      JSON список словарей
       - `type` : строка с типом контакта
       - `value` : строка со значением

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass


