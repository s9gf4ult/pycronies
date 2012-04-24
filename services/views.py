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
    execute_list_activity_resource_parameters, execute_change_resource_parameter, execute_conform_resource_parameter, \
    execute_create_contractor, execute_use_contractor,  execute_participant_statistics, \
    execute_contractor_offer_resource, execute_contractor_list_project_resources, execute_list_contractors, \
    execute_set_resource_costs, execute_check_user_exists, execute_ask_user_confirmation, execute_create_user_account, \
    execute_confirm_account, execute_authenticate_user, execute_confirm_user_by_long_confirmation

from services.common import getencdec, standard_request_handler, typical_json_responder, translate_parameters, parse_json, \
    translate_values, translate_string, proceed_checks, naive_json_responder
from services.models import Project, Resource
from django.conf import settings
from services.statuses import PARAMETERS_BROKEN
from svalidate import OrNone, Any, DateTimeString, RegexpMatch, Equal, JsonString, Able, Validate, Checkable, Each
from copy import copy
from django.core.validators import email_re
def is_valid_email(email):
    return True if isinstance(email, basestring) and email_re.match(email) else False

_good_string = RegexpMatch(r'^[^;:"''|\\/#&><]*$')
_good_float = Each(Able(float), Checkable(lambda a: float(a) >=0, 'Value must not be >= 0'))
_good_int = Each(Able(int), Checkable(lambda a: int(a) >= 0, 'Value must be >= 0'))
_is_email = Checkable(is_valid_email, 'String must be email')


@transaction.commit_on_success
@standard_request_handler({'name' : '',
                           'descr' : OrNone(''),
                           'begin_date' : OrNone(DateTimeString()),
                           'sharing' : Any(*[Equal(a[0]) for a in Project.PROJECT_SHARING]),
                           'ruleset' : Any(*[Equal(a[0]) for a in Project.PROJECT_RULESET]), # fucken amazing !
                           'user_name' : '',
                           'user_id' : OrNone(''),
                           'user_descr' : OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string,
                       'user_name' : translate_string,
                       'user_id' : translate_string,
                       'user_descr' : translate_string})
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
    - `user_id`: не обязательный token зарегистрированного пользователя
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
@standard_request_handler({'page_number' : OrNone(_good_int),
                           'projects_per_page' : OrNone(_good_int),
                           'status' : OrNone(Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS])),
                           'begin_date' : OrNone(DateTimeString()),
                           'search' : OrNone(_good_string)})
@translate_parameters({'search' : translate_string})
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
@standard_request_handler({'user_id' : ''})
@translate_parameters({'user_id' : translate_string})
@typical_json_responder(execute_list_user_projects, httplib.OK)
def list_user_projects_route(params): # ++TESTED
    """
    **Проекты пользователя**

    путь запроса: **/project/list/userid**

    Параметры запроса

    - `user_id`: token приглашения или токен зарегистрированного пользователя

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

    Статус 412

       Только BROKEN_PARAMETERS

    Posible return status:

    - `200`: ok
    - `412`: precondition failed, details in response body
    - `501`: query was not post
    - `500`: otherwise
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'status' : Any(*[Equal(a[0]) for a in Project.PROJECT_STATUS]),
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
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
                           'name' : '',
                           'descr' : OrNone(''),
                           'tp' : _good_string,
                           'enum' : JsonString(True),
                           'value' : _good_string,
                           # 'values' : OrNone(JsonString([{'value' : _good_string,
                           #                                'caption' : OrNone(_good_string)}])),
                           'caption' : OrNone(''),
                           'comment' : OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string,
                       'caption' : translate_string,
                       'comment' : translate_string})
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
       - `uuid`: uuid предложившего
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
                           'caption' : OrNone(''),
                           'comment' : OrNone('')})
@translate_parameters({'caption' : translate_string,
                       'comment' : translate_string})
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
def delete_project_route(params): #  NOTE: метод для тестов
    """
    get string with psid

    just for testing
    """
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
                           'name' : OrNone(''),
                           'descr' : OrNone(''),
                           'user_id' : OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string,
                       'user_id' : translate_string})
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
    - `user_id`: не обазательный token зарегистрированного пользователя,
      используется чтобы привязать участника проекта к существующему пользователю.
      Можно выполнять такое действие только тогда, когда `uuid` совпадает с uuid
      участника из `psid` или не указан (то есть редактируем сами себя)

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
       - `uuid`: (строка) uuid предлагающего
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
                           'name' : '',
                           'descr' : OrNone(''),
                           'email' : _is_email,
                           'comment': OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string,
                       'comment' : translate_string})
@typical_json_responder(execute_invite_participant, httplib.CREATED)
def invite_participant_route(params): # ++TESTED
    """
    **Пригласить участника**

    путь сервиса **/participant/invite**

    Принимает json словарь с ключами:

    - `psid`: (строка) ключ доступа
    - `name`: (строка) имя участника
    - `descr`: (строка) описание участника, может быть Null
    - `email`: (строка) почта пользователя куда слать приглашение
    - `comment`: (строка) комментарий по предложению, может быть Null

    В отладночном режиме озвращает json словарь с ключами:

    - `token`: (строка) ключ приглашения

    Ничего не возвращает в теле в нормальном режиме

    Поведение:

       Создает участника проекта с указанными данными и отправляет на указанный
       email письмо с кодом приглашения, если email принадлежит зарегистрированному
       пользователю, то создает участника проекта из этого пользователя.

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
                           'uuid' : OrNone(_good_string),
                           'vote' : Any(Equal('include'), Equal('exclude')),
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_conform_participant_vote, httplib.CREATED)
def conform_participant_vote_route(params):
    """
    **Подтвердить действие над участником**

    путь запроса: **/participant/vote/conform**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: не обязательный uuid участника
    - `vote`: "include" или "exclude", подтверждаем приглашение или
      исключение участника соответственно
    - `comment`: комментарий по приглашению, не обязательный


    Поведение:

       Если предложение на удаление или включение участника от имени вызывавшего
       сервис уже есть, то согласуем это предложение. Иначе создаем предложение
       и согласуем его.

       Если `uuid` не указан, то применяем действия к самому себе

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
                           'name' : '',
                           'descr' : OrNone(''),
                           'user_id' : OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string,
                       'user_id' : translate_string})
@typical_json_responder(execute_enter_project_open, httplib.CREATED)
def enter_project_open_route(params): # ++TESTED
    """
    **Вход на открытый проект**

    путь запроса: **/project/enter/open**

    Параметры запроса:

    - `uuid`: ид проекта
    - `name`: имя участника
    - `descr`: описание участника может быть None
    - `user_id`: не обязательный token зарегистрированного пользователя

    возвращает JSON словарь:

    - `psid`: ключ доступа
    - `token`: токен приглашения

    Статус 412:

    - PARTICIPANT_ALREADY_EXISTS: Пользователь с таким именем уже есть на проекте
    - PROJECT_MUST_BE_OPEN: не верный тип проекта
    - PROJECT_STATUS_MUST_BE_PLANNING: не верный статус проекта

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
    - `token`: токен приглашения или токен зарегистрированного пользователя

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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_exclude_participant, httplib.CREATED)
def exclude_participant_route(params): # ++TESTED
    """
    **Исключить участника**

    **NOTE: ** функция устаревшая, дублирует функциональность
    **/participant/vote/conform**

    **NOTE: ** дублиреут функциональность
    **/participant/vote/conform**

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
def list_activities_route(params): # ++TESTED
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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_activity_participation, httplib.CREATED)
def activity_participation_route(params): # ++TESTED
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
                           'name' : '',
                           'descr' : OrNone(''),
                           'begin' : DateTimeString(),
                           'end' : DateTimeString()})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string})
@typical_json_responder(execute_create_activity, httplib.CREATED)
def create_activity_route(params): # ++TESTED
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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_public_activity, httplib.CREATED)
def public_activity_route(params): # ++TESTED
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

       Если имеются голоса против мероприятия, то public работает как голос "за"
       мероприяте в проекте, инициатор в "despot" проектах сразу закрывает
       голоса против если вызовет public

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
def activity_delete_route(params): # ++TESTED
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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_activity_deny, httplib.CREATED)
def activity_deny_route(params): # ++TESTED
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
def list_activity_participants_route(params): # ++TESTED
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

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'name' : '',
                           'descr' : OrNone(''),
                           'tp' : _good_string,
                           'enum' : JsonString(True),
                           'value' : OrNone(_good_string)})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string})
def create_activity_parameter_route(params): # ++TESTED
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
def create_activity_parameter_from_default_route(params): # ++TESTED
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
def list_activity_parameters_route(params): # ++TESTED
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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_change_activity_parameter, httplib.CREATED)
def change_activity_parameter_route(params): # ++TESTED
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
                           'amount' : _good_float})
def include_personal_resource_route(params): # ++TESTED
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
def list_activity_resources_route(params): # ++TESTED
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
    - `product`: ид продукта
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
      если просматриваем список ресурсов по мероприятию а не по проекту
       - `name`: имя поставщика
       - `user`: user_id поставщика
       - `cost`: предложенная цена по ресурсу
       - `amount`: количетсво ресурса, согласованное для поставки данным поставщиком
       - `offer_amount`: количество ресурса, которое поставщик может поаставить,
         если None значит поставщик не ограничен в количестве ресурса
       - `votes`: предложения по этому поставщику
          - `uuid`: uuid пользователя
          - `amount`: количество ресурса предложенное участником проекта
            для поставки данным поставщиком. То есть сколько ресурса взять
            у данного поставщика.
    - `used`: Boolean, признак того, что ресурс используется
      на этом мероприятии, если просмотр не по мероприятию а по проекту, то
      возвращает True если общий ресурс использутся хотя бы на одном мероприятии
      либо персональный ресурс хотя бы одним участником в мероприятии
    - `amount`: Если указан `uuid`, то для общего ресурса - количество ресурса
      задействованное на конкретном мероприятии. Для персонального - количество
      ресурса задействованное конкретным участником.

      Если `uuid` не указан то для общего ресурса показывает суммарное количество
      ресурса задействованное на всех мероприятиях. Для персонального
      ресурса показывает суммарное количество ресурса задйествованное всеми
      участниками на всех мероприятиях
    - `available`: количество ресурса поставленное всеми
      поставщиками на проект, не возвращается для отчета по мероприятию
    - `cost`: цена, если выбран поставщик, не возвращается для просмотра по
      мероприятию, ибо не однозначно количество ресурса, которое надо отобразить
    - `min_cost`: минимальная цена за еденицу ресурса, выставленная инициатором
    - `min_cost_sum`: минимальная цена за весь объем заказанного ресурса
    - `max_cost`: максимальная цена за еденицу ресурса выставленная инициатором
    - `max_cost_sum`: максимальная цена за весь объем заказанного ресурса
    - `mean_cost`: предполагаемая цена за еденицу ресурса выставленная инициатором
    - `mean_cost_sum`: предполагаемая цена за весь объем заказанного ресурса

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'name' : '',
                           'descr' : OrNone(''),
                           'units' : _good_string,
                           'use' : Any(*[Equal(a[0]) for a in Resource.RESOURCE_USAGE]),
                           'site' : Any(*[Equal(a[0]) for a in Resource.RESOURCE_SITE])})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string})
@typical_json_responder(execute_create_project_resource, httplib.CREATED)
def create_project_resource_route(params): # ++TESTED
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
                           'amount' : OrNone(_good_float),
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
def include_activity_resource_route(params): # ++TESTED
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
                           'comment' : OrNone('')})
@translate_parameters({'comment' : translate_string})
@typical_json_responder(execute_exclude_activity_resource, httplib.CREATED)
def exclude_activity_resource_route(params): # ++TESTED
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
                           'value' : OrNone(_good_string),
                           'values' : OrNone(JsonString([{'value' : _good_string,
                                                          'caption' : OrNone('')}]))})
@translate_parameters({'values' : translate_values,
                       'enum' : parse_json})
@proceed_checks({'lambda' : lambda a: a['values'] != None and len(a['values']) > 0 if a['enum'] else True,
                 'caption' : 'if `enum` is True then `values` must be list of at least one element'})
@typical_json_responder(execute_create_resource_parameter, httplib.CREATED)
def create_activity_resource_parameter_route(params): # ++TESTED
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
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'activity' : _good_string,
                           'uuid' : _good_string,
                           'default' : _good_string})
@typical_json_responder(execute_create_resource_parameter_from_default, httplib.CREATED)
def create_activity_resource_parameter_from_default_route(params): # ++TESTED
    """
    **Добавить типовой параметр ресурса**

    путь запроса: **/activity/resource/parameter/create/fromdefault**

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
def list_activity_resource_parameters_route(params): # ++TESTED
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
                           'caption' : OrNone(''),
                           'comment' : OrNone('')})
@translate_parameters({'caption' : translate_string,
                       'comment' : translate_string})
@typical_json_responder(execute_change_resource_parameter, httplib.CREATED)
def change_resource_parameter_route(params): # ++TESTED
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
def conform_resource_parameter_route(params): # ++TESTED
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
                           'contractor' : '',
                           'amount' : OrNone(_good_float),
                           'comment' : OrNone('')})
@translate_parameters({'amount' : float,
                       'comment' : translate_string,
                       'contractor' : translate_string})
@typical_json_responder(execute_use_contractor, httplib.CREATED)
def use_contractor_route(params): # ++TESTED
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
    - `comment`: не обязательный комментарий пользователя, почему именно
      этот поставщик, ну или типа того

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass


# @transaction.commit_on_success
# @standard_request_handler({'psid' : _good_string})
# @typical_json_responder(execute_report_project_statistics, httplib.OK)
# def project_statistics_route(params):
#     """
#     **Отчет о пректе**

#     путь запроса: **/project/report**

#     Параметры запроса:

#     - `psid`: ключ доступа к проекту

#     Вовзращает JSON словарь с ключами:

#     - `uuid`: ид проекта
#     - `name`: имя проекта
#     - `descr`: описание проекта
#     - `sharing`: строка, описывает политику добавления новых участников проекта
#        - `open`: проект открыт для свободного доступа
#        - `invitation`: проект доступен для входа по приглашениям
#        - `close`: доступом в проект упаравляет инициатор
#     - `ruleset`: политика управления свойствами проекта
#        - `despot`: всем управляет инициатор
#        - `auto`: авто управление
#        - `vote`: управление голосованием
#     - `begin_date`: дата старта проекта
#     - `end_date`: дата завершения проекта
#     - `cost`: цена всего проекта (цена ресурсов)
#     - `resources`: описывает ресурсы задействованные на проекте,
#       то есть только те ресурсы, которые используются хотя бы одним мероприятием
#       или участником мероприятия, в количестве более 0.001. Является списком хэш
#       таблиц с ключами:
#        - `uuid`: uuid ресурса
#        - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
#        - `amount`: суммарное количество ресурса использованное на проекте
#        - `available`: количество ресурса заказанное на поставку
#        - `cost`: цена ресурса, если есть поставщик, None если поставщика нет
#        - `name`: имя ресурса
#        - `descr`: описание ресурса
#        - `units' : название еденицы измерения ресурса
#        - `use` : способ использования ресурса, одно из возможных значений:
#           - `common`: общий ресурс для мероприятия
#           - `personal`: ресурс персональный
#        - `site`: принадлежность ресурса, строка, одно из возможных значений
#           - `internal`: ресурс внутренний, покупать не нужно
#           - `external`: ресурс нужно еще приобрести

#     Статусы возврата:

#     - `200`: ok
#     - `412`: не верные данные с описанием в теле ответа
#     - `500`: ошибка сервера

#     """
#     pass

# @transaction.commit_on_success
# @standard_request_handler({'psid' : _good_string,
#                            'uuids' : OrNone(JsonString([_good_string]))})
# @translate_parameters({'uuids' : parse_json})
# @typical_json_responder(execute_activity_statistics, httplib.OK)
# def activity_statistics_route(params):
#     """
#     **Отчет по мероприятию / мероприятиям**

#     путь запроса: **/activity/report**

#     Параметры запроса:

#     - `psid`: ключ доступа
#     - `uuids`: не обязательный JSON список uuid мероприятий для получения
#       отчета только по выбранным мероприятиям, если не указан или пустой,
#       то возвращается отчет по всем мероприятиям выбранного проекта

#     Возвращает JSON кодированный спимок словарей с ключами:

#     - `uuid`: ид мероприятия
#     - `name`: имя мероприятия
#     - `descr`: описание мероприятия
#     - `begin`: дата начала мероприятия ISO строка
#     - `end`: дата окончания мероприятия ISO дата строкой
#     - `resources`: ресурсы мероприятия и личные ресрусы которые используются на этом мероприятии,
#       список словарей с ключами:
#        - `uuid`: uuid ресурса
#        - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
#        - `amount`: суммарное количество ресурса использованное на мероприятии
#        - `name`: имя ресурса
#        - `descr`: описание ресурса
#        - `units' : название еденицы измерения ресурса
#        - `use` : способ использования ресурса, одно из возможных значений:
#           - `common`: общий ресурс для мероприятия
#           - `personal`: ресурс персональный
#        - `site`: принадлежность ресурса, строка, одно из возможных значений
#           - `internal`: ресурс внутренний, покупать не нужно
#           - `external`: ресурс нужно еще приобрести

#     Статусы возврата:

#     - `200`: ok
#     - `412`: не верные данные с описанием в теле ответа
#     - `500`: ошибка сервера

#     """
#     pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuids' : OrNone(JsonString([_good_string]))})
@translate_parameters({'uuids' : parse_json})
@typical_json_responder(execute_participant_statistics, httplib.OK)
def participant_statistics_route(params):
    """
    **Отчет по пользователю / пользователям**

    путь запроса: **/participant/report**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuids`: JSON список uuid пользователей, если не указан или пустой,
      возвращается отчет по всем пользователям

    Возвращет JSON словарь с ключами:

    - `participants`: участники с подробными данными по ним, список словарей с ключами
       - `uuid`: ид пользователя
       - `create`: дата входа пользователя на проект, ISO строка
       - `login`: дата последнего логина пользователя, ISO строка либо None
         (участник не логинился)
       - `is_initiator`: Boolean является ли пользователель инициатором
       - `user_id`: user_id пользователя
       - `name`: имя (ник) пользователя
       - `descr`: описание пользователя
       - `status`: статус участника проекта
       - `cost`: цена за все ресурсы на проекте для этого пользователя
       - `resources`: ресурсы мероприятия и личные ресрусы которые используются на этом мероприятии,
         список словарей с ключами:
          - `uuid`: uuid ресурса
          - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
          - `amount`: суммарное количество ресурса затребованное данным участником,
            персональные ресурсы просто складываются, тогда как для общих ресурсов
            вычисляется среднее значение количества ресурса использованное данным
            участником на данном мероприятии. Например пользователь учавствует в 2х
            мероприятиях, в одном мероприятии 10 участников во втором 15, в первом
            мероприятии используется ресурс А в поличестве 100, на втором
            используется ресурс Б в количетсве 30, тогда ресурс А используется
            каждым участником мероприятия в количестве 100 / 10 = 10, а ресурс Б
            30 / 15 = 2. Потому что каждый участник в равной степени использует общий
            ресурс каждого мероприятия
          - `available`: то же что `amount` но помноженное на процент поставки, то есть
            на отношение общего необходимого количества товара к общему количеству
            поставленного товара
          - `cost`: общая цена товара умноженная на отношение общего количества
            поставленного товара к количеству поставленного этому участнику товара
            `available`
          - `min_cost`: минимальная цена за ресурс заказанный участником
          - `max_cost`: минимальная цена за ресурс заказанный участником
          - `mean_cost`: минимальная цена за ресурс заказанный участником
          - `name`: имя ресурса
          - `descr`: описание ресурса
          - `units` : название еденицы измерения ресурса
          - `use` : способ использования ресурса, одно из возможных значений:
             - `common`: общий ресурс для мероприятия
             - `personal`: ресурс персональный
          - `site`: принадлежность ресурса, строка, одно из возможных значений
             - `internal`: ресурс внутренний, покупать не нужно
             - `external`: ресурс нужно еще приобрести
    - `resources`: список словарей с ключами:
       - `uuid`: uuid ресурса
       - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
       - `amount`: суммарное количество ресурса затребованное списом участников
       - `available`: суммароное количество поставленного ресурса для списка
         участников
       - `cost`: общая цена товара для списка участников
       - `min_cost`: минимальная цена за весь объем ресурса
       - `max_cost`: максимальная цена за весь объем ресурса
       - `mean_cost`: предполагаемая цена за весь объем ресурса
       - `name`: имя ресурса
       - `descr`: описание ресурса
       - `units` : название еденицы измерения ресурса
       - `use` : способ использования ресурса, одно из возможных значений:
          - `common`: общий ресурс для мероприятия
          - `personal`: ресурс персональный
       - `site`: принадлежность ресурса, строка, одно из возможных значений
          - `internal`: ресурс внутренний, покупать не нужно
          - `external`: ресурс нужно еще приобрести

    - `cost`: суммарная цена по всем участникам, если не указан `uuids` то по сути
      является ценой всех ресурсов на проекте
    - `min_cost`: минимальная цена за все ресуры
    - `max_cost`: максимальная цена за все ресурсы
    - `mean_cost`: предполагаемая цена за все ресурсы

    Повещение

       Если указан `uuids` то выводит статистику строго по пользователям из
       списка, не найденные пользователи просто игнорируются.  Если `uuids` не
       казан, то выводит статистику по активным пользователям (статус accepted),
       в обоих случаях выводит только пользователей находящихся в проекте
       привязанном к `psid`

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера

    """
    pass

@transaction.commit_on_success
@standard_request_handler({'uuid' : _good_string})
@typical_json_responder(execute_contractor_list_project_resources, httplib.OK)
def contractor_list_project_resources_route(params): # ++TESTED
    """
    **Просмотр ресурсов проекта для поставщика**

    путь запроса: **/contractor/project/resource/list**

    Параметры запроса:

    - `uuid`: ид проекта для просмотра ресурсов

    Результат JSON список словарей

    - `uuid`: uuid ресурса
    - `product`: ид продукта (для связи с таблицей продуктов от поставщиков)
    - `amount`: суммарное количество ресурса требуемое на проекте
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
                           'cost' : _good_float,
                           'amount' : OrNone(_good_float)})
@translate_parameters({'amount' : float,
                       'cost' : float})
@typical_json_responder(execute_contractor_offer_resource, httplib.CREATED)
def contractor_offer_resource_route(params): # ++TESTED
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
@standard_request_handler({'user' : '',
                           'name' : '',
                           'contacts' : OrNone(JsonString([{'type' : _good_string,
                                                            'value' : _good_string}]))})
@translate_parameters({'contacts' : parse_json,
                       'user' : translate_string,
                       'name' : translate_string})
@typical_json_responder(execute_create_contractor, httplib.CREATED)
def create_contractor_route(params): # ++TESTED
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

@transaction.commit_on_success
@typical_json_responder(execute_list_contractors, httplib.OK)
def list_contractors(params):   # ++TESTED
    """
    **Список поставщиков**

    путь запроса: **/contractor/list**

    Параметров нет, возвращает JSON список словарей

    - `user`: user_id поставщика
    - `name`: имя поставщика
    - `contacts`: список контактов поставщика
       - `type`: тип контакта (mail, telephone, ...
       - `value`: значение контакта

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера

    """
    pass


@transaction.commit_on_success
@standard_request_handler({'psid' : _good_string,
                           'uuid' : _good_string,
                           'min' : OrNone(_good_int),
                           'max' : OrNone(_good_int),
                           'cost' : OrNone(_good_int)})
@translate_parameters({'min' : float,
                       'max' : float,
                       'cost' : float})
@typical_json_responder(execute_set_resource_costs, httplib.CREATED)
def set_resource_costs_route(params):
    """
    ** Сменить предполагаемые цены на ресурс **

    путь запроса: **/resource/cost/change**

    Параметры запроса:

    - `psid`: ключ доступа
    - `uuid`: uuid ресурса
    - `min`: минимальная предполагаемая цена на ресурс
    - `max`: максимальная предполагаемая цена за ресурс
    - `cost`: предполагаемая цена за ресурс

    Статусы возврата:

    - `201`: ok
    - `412`: не верные данные с описанием в теле ответа
    - `501`: если управление проектом != "despot"
    - `500`: ошибка сервера
    """
    pass


@transaction.commit_on_success
@standard_request_handler({'email' : _is_email})
@naive_json_responder(execute_check_user_exists)
def check_user_exists_route(params):
    """
    ** Проверка существования пользователя по Email **

    путь запроса: **/user/check**

    Параметры запроса:

    - `email`: электронная почта пользователя

    Статусы возврата:

    - `200`: пользователь существует
    - `404`: нет такого пользователя
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'email' : _is_email,
                           'password' : '',
                           'name' : '',
                           'descr' : OrNone('')})
@translate_parameters({'name' : translate_string,
                       'descr' : translate_string})
@typical_json_responder(execute_create_user_account, httplib.CREATED)
def create_user_account_route(params):
    """
    ** Создание пользователя **

    путь запроса: **/user/new**

    Параметры зпароса:

    - `email`: электронная почта пользователя (она же логин)
    - `password`: пароль
    - `name`: имя / ник
    - `descr`: не обязательное описание пользователя

    Возвраащет json словарь с данными пользователя

    - `email`: электронная почта пользователя (она же логин)
    - `name`: имя / ник
    - `descr`: описание пользователя

    Статусы возврата:

    - `201`: ok
    - `409`: такой email уже есть
    - `412`: не верные данные с описанием в теле ответа
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'email' : _is_email})
@typical_json_responder(execute_ask_user_confirmation, httplib.OK)
def ask_user_confirmation(params):
    """
    ** Отправка писма для подтверждения **

    путь запроса: **/user/ask_confirm**

    Параметры запроса:

    - `email`: электронная почта зарегистрированного пользователя

    В отладочном режиме возвращает словарь

    - `confirmation`: код подтверждения который отправляется
      на email пользователя

    Статусы возврата:

    - `200`: ok
    - `409`: пользователь уже подтвержден
    - `412`: не верные данные с описанием в теле ответа либо ошибка
      отправки письма, подробности в теле
    - `500`: ошибка сервера
    """
    pass


@transaction.commit_on_success
@standard_request_handler({'email' : _is_email,
                           'password' : '',
                           'confirmation' : ''}) #  FIXME: Этот метод одлжен
                                        #  принимать специальный confirmation
                                        #  для ручного ввода (типа короткий и
                                        #  легко вводимый
@typical_json_responder(execute_confirm_account, 202)
def confirm_account_route(params):
    """
    ** Активация аккаунта **

    путь запроса: **/user/confirm**

    Параметры зпароса:

    - `email`: почта пользователя
    - `password`: пароль пользователя
    - `confirmation`: ключ подтверждения (приходит на почту)

    При успешном создании пользователя ничего не возвращает в теле

    Статусы возврата:

    - `202`: ok
    - `412`: подтверждение не прошло либо ошибка в параметрах
    - `500`: ошибка сервера
    """
    pass

@transaction.commit_on_success
@standard_request_handler({'email' : _is_email,
                           'password' : ''})
@typical_json_responder(execute_authenticate_user, httplib.OK)
def authenticate_user_route(params):
    """
    ** Аутентификация пользователя **

    путь запроса: **/user/auth**

    Параметры запроса:

    - `email`: почта она же логин
    - `password`: пароль пользователя

    Возвращает json словарь с ключами:

    - `email` : почта
    - `name`: имя пользователя
    - `descr`: описание пользователя
    - `token`: ключ доступа пользователя

    Статусы возврата:

    - `200`: ok
    - `412`: не верные данные с описанием в теле ответа либо ошибка другого рода
    - `500`: ошибка сервера
    """
    pass


def invitation_response_route(request, invite):
    r = http.HttpResponseRedirect(settings.MY_ROOT_PATH)
    r.set_cookie('invitation', invite, httponly = False)
    return r

@transaction.commit_on_success
def confirmation_response_route(request, confirmation):
    ret, st = execute_confirm_user_by_long_confirmation(confirmation)
    if st == 200:
        cnf = True
    else:
        transaction.rollback()
        cnf = False
        
    r = http.HttpResponseRedirect(settings.MY_ROOT_PATH)
    r.set_cookie('confirmation', cnf, httponly = False)
    return r
        
