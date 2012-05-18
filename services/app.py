#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import get_or_create_object, get_user, get_authorized_user, \
    get_object_by_uuid, get_activity_from_uuid, get_activity_parameter_from_uuid, string2datetime, create_object_parameter, \
    set_object_status, set_object_parameter, get_object_status, get_object_parameter, create_object_parameter_from_default, \
    set_vote_for_object_parameter, get_vote_value_for_object_parameter, set_as_accepted_value_of_object_parameter, \
    get_or_create_object_parameter, get_resource_from_uuid, get_activity_resource_from_parameter, check_activity_resource_status, \
    get_authorized_activity_participant, get_resource_parameter_from_uuid, get_parameter_voter, am_i_creating_activity_now, \
    create_user, get_database_user, get_acceptable_user, auth_user, generate_user_magic_link, send_mail, get_registered_user, \
    return_if_debug
from services.models import Project, Participant, hex4, ProjectParameter, ProjectParameterVl, ProjectParameterVal, \
    DefaultParameter,  DefaultParameterVl, ProjectRulesetDefaults, ProjectParameterVote, ActivityParticipant, \
    Activity, ActivityParameter, ActivityParameterVal, ActivityParameterVl, ActivityParameterVote, ParticipantParameterVal, \
    Resource, MeasureUnits, ActivityResourceParameterVote, ParticipantResource, ActivityResource, ActivityResourceParameter, \
    ParticipantResourceParameter, Contractor, ContractorUsagePrmtVote, ContractorContact, ContractorOffer, ContractorUsage, User
from services.statuses import *
from django.db import transaction, IntegrityError
from django.contrib.sites.models import Site
from django.db.models import Q, Sum
from django.conf import settings
from datetime import datetime
from math import ceil
import httplib
from copy import copy


def execute_create_project(parameters):
    """create project and related objects based on parameters

    Arguments:

    - `parameters`: dict with parametes
    """
    # создаем проект
    p = Project(name = parameters['name'], sharing=parameters['sharing'],
                ruleset=parameters['ruleset'])
    if 'descr' in parameters:
        p.descr = parameters['descr']
    if 'begin_date' in parameters:
        p.begin_date = string2datetime(parameters['begin_date'])
    else:
        p.begin_date=datetime.now()
    p.save(force_insert=True)

    # создаем участника - владельца
    pr = Participant(project=p, name=parameters['user_name'])
    pr.psid=hex4()
    pr.token=hex4()
    pr.is_initiator=True
    if parameters.get('user_id') != None:
        try:
            u = User.objects.filter(token=parameters['user_id']).all()[0]
        except IndexError:
            return {'code' : AUTHENTICATION_FAILED,
                    'caption' : 'This token is not allowerd'}, httplib.PRECONDITION_FAILED
        else:
            pr.user = u
    if parameters.get('user_descr') != None:
        pr.descr = parameters['user_descr']
    pr.save(force_insert=True)

    create_object_parameter(p, 'status', True, values = [{'value' : a[0]} for a in Project.PROJECT_STATUS])
    create_object_parameter(pr, 'status', True, values = [{'value' : a[0]} for a in Participant.PARTICIPANT_STATUS])

    set_object_status(p, pr, 'opened')
    set_object_status(pr, pr, 'accepted')

    # заполняем дефолтные параметры проекта
    for prd in ProjectRulesetDefaults.objects.filter(Q(ruleset=p.ruleset) | Q(ruleset=None)).all():
        dpr = prd.parameter
        prmt = create_object_parameter_from_default(p, dpr)
        if dpr.default_value != None:
            try:
                set_object_parameter(p, pr, dpr.default_value, uuid=prmt.uuid)
            except ValueError:
                return {'code' : PROJECT_PARAMETER_ERROR,
                        'caption' : 'It seems that database has wrong default parameters for project'}, httplib.PRECONDITION_FAILED

    return {'uuid' : p.uuid,
            'psid' : pr.psid,
            'token' : pr.token}, httplib.CREATED

def execute_list_projects(props):
    """select projects and return data
    return list of hash tables to serialize
    Arguments:
    - `props`:
    """
    def none_and(fst, snd):
        if fst==None:
            return snd
        else:
            return (fst & snd)

    qry = None     # сформированное условие для отбора
    if props.get('status') != None:
        qry = none_and(qry, (Q(projectparameter__tpclass='status') & Q(projectparameter__projectparameterval__status='accepted') & Q(projectparameter__projectparameterval__value=props['status'])))
    if props.get('begin_date') != None:
        qry = none_and(qry, Q(begin_date__gte = string2datetime(props['begin_date'])))
    if props.get('search') != None:
        qry = none_and(qry, (Q(name__contains=props['search']) | Q(descr__contains=props['search'])))
    if props.get('uuid') != None:
        qry = none_and(qry, Q(uuid=props['uuid']))
    else:
        qry = none_and(qry, Q(sharing='open'))

    qr = None                   # сформированный запрос для выборки
    if qry == None:
        qr = Project.objects.all()
    else:
        qr = Project.objects.filter(qry).all()

    count = qr.count()
    ret = None                                 # запрос с ограниченным количеством проектов
    if props.get('projects_per_page') != None: # указано количество пректов на страницу
        pn = props.get('page_number') if props.get('page_number') != None else 0 # номер страницы
        ppp = props['projects_per_page'] # количество проектов на страницу
        if count < pn*ppp:
            try:
                return {'pages' : int(ceil(float(count) / ppp)),
                        'projects' : []} # количество проектов меньше чем начало
# куска который был запрошел
            except ZeroDivisionError:
                return {'pages' : 0,
                        'projects' : []}
        ret = qr[ppp*pn:ppp*(pn+1)]
    else:                       # количество проектов на страницу не указано
        ret = qr
    try:
        pagesc = int(ceil(float(count) / props.get('projects_per_page'))) if props.get('projects_per_page') != None else count
    except ZeroDivisionError:
        pagesc = 0
    return {'pages' : pagesc,
            'projects' : [{'uuid' : a.uuid,
                           'name' : a.name,
                           'descr' : a.descr,
                           'sharing' : a.sharing,
                           'ruleset': a.ruleset,
                           'participants' : a.participant_set.count(),
                           'begin_date' : a.begin_date.isoformat() if a.begin_date != None else None,
                           'end_date' : a.end_date.isoformat() if a.end_date != None else None} for a in ret]}

def execute_list_user_projects(params):
    """return tuple of response and status
    response is json encodable answer, list of projects assigned to given user_id

    Arguments:

    - `user_id`:

    Return:

    (`response`, `answer`)
    """
    # берем список участников с указанным user_id
    user_id = params['user_id']
    parts = Participant.objects.filter(Q(user__token=user_id) | Q(token=user_id)).all() # список участиков
    ret = []
    # формируем список проектов для соответствующего списка участников
    for part in parts:
        pr = part.project # связанный проект
        ret.append({'uuid' : pr.uuid,
                    'name' : pr.name,
                    'descr' : pr.descr,
                    'participants' : pr.participant_set.count(),
                    'begin_date' : pr.begin_date.isoformat() if pr.begin_date != None else None,
                    'initiator' : part.is_initiator,
                    'status' : get_object_status(pr)})
    ret.sort(lambda a, b: cmp(a['name'], b['name']))
    return ret, httplib.OK

@get_user
def execute_change_project_status(params, part):
    """
    - `params`:
    """
    # если участник не инициатор - выходим
    if part.is_initiator == False:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : u'this user is not initiator'}, httplib.PRECONDITION_FAILED
    prj = part.project
    # если проект не управляемый - выходим
    if prj.ruleset != 'despot':
        return {'code' : WRONG_PROJECT_RULESET,
                'caption' : u'project ruleset is not "despot"'}, httplib.PRECONDITION_FAILED
    # меняем статус проекта
    set_object_status(prj, part, params['status'], params.get('comment'))
    return 'OK', httplib.CREATED

def execute_list_default_parameters():
    """return list of dicts with default parameters
    """
    ret=[]
    for defpr in DefaultParameter.objects.all():
        a = {'uuid' : defpr.uuid,
             'name' : defpr.name,
             'descr' : defpr.descr,
             'tp' : defpr.tp,
             'enum' : defpr.enum,
             'default' : defpr.default_value}
        if defpr.enum:
            x = []
            for enpr in DefaultParameterVl.objects.filter(parameter=defpr).all():
                x.append({'value' : enpr.value,
                          'caption' : enpr.caption})
            a['values'] = x
        ret.append(a)
    return ret

@get_user
@get_object_by_uuid(DefaultParameter,
                    DEFAULT_PARAMETER_NOT_FOUND,
                    u'There is no such default parameter')
def execute_create_project_parameter_from_default(params, dpr, part):
    """
    Arguments:

    - `params`:
    """
    return create_project_parameter_from_default(params, dpr, part)

def create_project_parameter_from_default(params, dpr, part):

    prj = part.project

    if prj.ruleset == 'despot':
        return despot_create_project_parameter_from_default(params, dpr, part)
    else:
        return 'This method is not implemented for ruleset {0}'.format(prj.ruleset), httplib.NOT_IMPLEMENTED

def despot_create_project_parameter_from_default(params, dpr, part):

    prj = part.project

    if not part.is_initiator:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : 'Your are not initiator to do this'}, httplib.PRECONDITION_FAILED

    try:
        prmt = create_object_parameter_from_default(prj, dpr)
    except IntegrityError:
        return {'code' : PROJECT_PARAMETER_ALREADY_EXISTS,
                'caption' : 'Default parameter correlate with existing one, can not create parameter with same name'}, httplib.PRECONDITION_FAILED
    if dpr.default_value != None:
        try:
            set_object_parameter(prj, part, dpr.default_value, uuid = prmt.uuid)
        except ValueError:
            return {'code' : PROJECT_PARAMETER_ERROR,
                    'caption' : 'This default parameter has wrong default value to set (not in enumerable list)'}, httplib.PRECONDITION_FAILED

    return 'OK', httplib.CREATED

@get_user
def execute_create_project_parameter(params, part):
    """
    Arguments:
    - `params`:
    """
    return create_project_parameter(params, part)

def create_project_parameter(params, part):
    # выбираем проект для соответствующего пользователя
    proj = part.project
    # проверяем тип проекта и вызываем соответствующий обработчик
    if proj.ruleset == 'despot':
        return despot_create_project_parameter(part, params)
    else:
        return u'Create project parameter is not implemented for ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED

def despot_create_project_parameter(user, params):
    """
    create parameter for despot ruleset project
    Arguments:
    - `params`:
    """
    # проверяем является ли пользователь инициатором
    if user.is_initiator == False:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : u'You must be initiator if project is "despot" ruleset'}, httplib.PRECONDITION_FAILED

    proj = user.project
    try:
        values = [] if (not params['enum']) else params['values']
        ppar = create_object_parameter(proj, 'user', False,
                                       tp = params['tp'],
                                       name = params['name'],
                                       descr = params.get('descr'),
                                       values = values)
    except IntegrityError:
        return {'code' : PROJECT_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exist'}, httplib.PRECONDITION_FAILED

    if params.get('value') != None:
        # вызываем изменение значения параметра
        return despot_change_project_parameter({'psid' : params['psid'],
                                                'uuid' : ppar.uuid,
                                                'value' : params['value'],
                                                'caption' : params.get('caption')}, user)
    else:
        return u'Created', httplib.CREATED

@get_user
@get_object_by_uuid(ProjectParameter,
                    PROJECT_PARAMETER_NOT_FOUND,
                    u'There is no such parameter')
def execute_change_project_parameter(params, par, user):
    """
    Arguments:
    - `params`:
    """
    # проверяем отностися ли параметр к проекту указанного пользователя
    proj = user.project
    if par.obj != proj:
        return {'code' : ACCESS_DENIED,
                'caption' : u'This user can not change specified parameter'}, httplib.PRECONDITION_FAILED
    # выбираем обработчик для соответствующего типа проекта
    if proj.ruleset == 'despot':
        return despot_change_project_parameter(params, user)
    else:
        return u'Change parameter is not implemented for project with ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED

def despot_change_project_parameter(params, user):

    proj = user.project
    try:
        set_vote_for_object_parameter(proj, user, params['value'], uuid = params['uuid'], caption = params.get('caption'))
    except ValueError:
        return {'code' : PROJECT_PARAMETER_ERROR,
                'caption' : 'This value not in accepted list of values for this parameter'}, httplib.PRECONDITION_FAILED
    except IndexError:
        return {'code' : PROJECT_PARAMETER_NOT_FOUND,
                'caption' : 'There is no such parameter'}, httplib.PRECONDITION_FAILED
    return despot_conform_project_parameter(params, user)

@get_user
@get_object_by_uuid(ProjectParameter,
                    PROJECT_PARAMETER_NOT_FOUND,
                    u'There is no such parameters')
def execute_conform_project_parameter(params, pr, part):
    # проверяем есть ли такой параметр и находиться ли он в том же проекте что и пользователь
    proj = part.project
    if pr.obj != proj:
        return {'code' : ACCESS_DENIED,
                'caption' : u'Parameter is not assigned to specified project'}, httplib.PRECONDITION_FAILED
    # вызываем обработчик для соответствующего типа проекта
    if proj.ruleset == 'despot':
        return despot_conform_project_parameter(params, part)
    else:
        return u'conform parameter is not implemented for ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED


def despot_conform_project_parameter(params, user):
    # если пользователь - инициатор: присваиваем предложенное пользователем значение как текущее значение параметра
    prj = user.project
    if user.is_initiator:
        # проверяем есть ли предложенные значения
        vtval = get_vote_value_for_object_parameter(prj, user, uuid = params['uuid'])
        if vtval == None:
            return u'There is nothing to conform (no votes)', httplib.CREATED
        # если есть присваиваем ему статус accepted, остальным присваиваем denied
        set_as_accepted_value_of_object_parameter(vtval)
        return u'Accepted new value', httplib.CREATED
    else:                                 #пользователь не инициатор - согласование ничего неделает
        return u'User is not initiator, do nothing', httplib.CREATED

@get_user
def execute_list_project_parameters(params, part):
    proj = part.project
    ret = []
    for param in ProjectParameter.objects.filter(Q(obj=proj) & Q(tpclass='user')).all():
        p = {'uuid' : param.uuid,
             'name' : param.name,
             'descr' : param.descr,
             'tp' : param.tp,
             'enum' : param.enum}
        if param.default == None:
            p['tecnical'] = False
        else:
            p['tecnical'] = param.default.tecnical
        if param.enum:          # параметр перечисляемый - добавляем возможные значения
            vs = []
            for v in ProjectParameterVl.objects.filter(parameter=param).all():
                vs.append({'value': v.value,
                           'caption' : v.caption})
            p['values'] = vs
        try:
            pv = ProjectParameterVal.objects.filter(Q(parameter=param) & Q(status='accepted')).all()[0]
            p['value'] = pv.value
            p['caption'] = pv.caption
        except IndexError:      # если не нашли значения просто игнорим
            pass
        votes = []
        for vts in ProjectParameterVal.objects.filter(Q(parameter=param) & Q(status='voted')).all(): # проходим по предложенным значениям
            for voter in vts.projectparametervote_set.all(): # проходим по предложившим
                v = {'uuid', voter.uuid,
                     'value', vts.value,
                     'caption', vts.caption}
                if vts.dt != None:
                    v['dt'] = vts.dt.isoformat()
                votes.append(v)
        p['votes'] = votes

        ret.append(p)
    return ret, httplib.OK

@get_user
def execute_change_participant(params, user):
    prj = user.project
    par = None
    if params.get('uuid') == None:
        par = user
    else:
        if Participant.objects.filter(uuid=params['uuid']).count() == 0:
            return {'code' : PARTICIPANT_NOT_FOUND,
                    'caption' : 'There is no such participant'}, httplib.PRECONDITION_FAILED
        par = Participant.objects.filter(uuid=params['uuid']).all()[0]
        if par.project != user.project:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You can not change this participant'}, httplib.PRECONDITION_FAILED

    def check_user(par, user):
        # проверка того, что пользователь меняет себя или приглашенного, который еще не входил
        if par.uuid == user.uuid:
            return True
        if par.project != user.project:
            return False
        if par.dt == None:      # целевой участник проекта еще не входил
            return True
        return False

    if not check_user(par, user):
        return {'code' : ACCESS_DENIED,
                'caption' : u'You can not change this user'}, httplib.PRECONDITION_FAILED
    # изменяем параметр пользователя
    if params.get('name') != None:
        par.name = params['name']
    if params.get('descr') != None:
        par.descr = params['descr']
    if params.get('user_id') != None:
        try:
            u = User.objects.filter(token = params['user_id']).all()[0]
        except IndexError:
            return {'code' : AUTHENTICATION_FAILED,
                    'caption' : 'Given token is not accepted'}, httplib.PRECONDITION_FAILED
        else:
            par.user = u
    try:
        par.save(force_update = True)
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'Participant with such name already exists'}, httplib.PRECONDITION_FAILED

    return 'OK', httplib.CREATED

# @get_user
def execute_list_participants(params):
    user = None
    if params.get('psid') != None:
        user = get_authorized_user(params['psid'])
        if user == None:
            return 'Participant not found', httplib.NOT_FOUND
        elif user == False:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'This user is not allowed'}, httplib.PRECONDITION_FAILED
        prj = user.project
    elif params.get('uuid') != None:
        try:
            prj = Project.objects.filter(uuid = params['uuid']).all()[0]
        except IndexError:
            return {'code' : PROJECT_NOT_FOUND,
                    'caption' : 'Project not found'}, httplib.PRECONDITION_FAILED
        else:
            if prj.sharing != 'open':
                return {'code' : PROJECT_MUST_BE_OPEN,
                        'caption' : 'You can not see this project'}, httplib.PRECONDITION_FAILED
    else:
        return {'code' : PARAMETERS_BROKEN,
                'caption' : 'You must specify at least `psid` or `uuid` parameter'}, httplib.PRECONDITION_FAILED
    
    ret = []
    # получаем список участников проекта
    for par in Participant.objects.filter(project=prj).all():
        a = {'uuid' : par.uuid,
             'name' : par.name,
             'descr' : par.descr,
             'me' : user.uuid == par.uuid if user != None else False,
             'status' : get_object_status(par)}

        # смотрим список предложений по участнику
        vts = []
        for ps in ParticipantParameterVal.objects.filter(Q(parameter__tpclass='status') & Q(parameter__obj=par) & Q(status='voted')).all(): #все предложенные статусы участника
            for pvt in ps.participantparametervote_set.all():   #все предложения по каждому статусу
                vts.append({'uuid' : pvt.voter.uuid,
                            'vote' : 'include' if ps.value == 'accepted' else 'exclude',
                            'comment' : pvt.comment})
        a['votes'] = vts
        ret.append(a)

    return ret, httplib.OK

@get_user
def execute_invite_participant(params, user):
    reguser = get_registered_user(params['psid'])
    if reguser == None or (not reguser.is_active):
        return {'code' : REGISTRATION_IS_REQUIRED,
                'caption' : 'You are not registered user, please register first'}, httplib.PRECONDITION_FAILED
    prj = user.project
    if prj.sharing == 'close':  # проект закрытый
        if prj.ruleset == 'despot' and (not user.is_initiator):
            return {'code' : MUST_BE_INITIATOR,
                    'caption' : 'You must be initiator to invite users to the close project'}, httplib.PRECONDITION_FAILED
    else:                       # проект открытый или по приглашению
        if  get_object_status(prj) != 'planning':
            return {'code' : PROJECT_STATUS_MUST_BE_PLANNING,
                    'caption' : 'Project is not in the planning status'}, httplib.PRECONDITION_FAILED

    # берем user_id по почте
    try:
        u = User.objects.filter(email = params['email']).all()[0]
    except IndexError:
        u = None
    # создаем нового или берем существующего участника
    try:
        def check(p):
            return prj.ruleset == 'despot' and user.is_initiator

        part = get_or_create_object(Participant,
                                    {'name' : params['name'],
                                     'project' : prj},
                                    {'descr' : params.get('descr'),
                                     'user' : u},
                                    can_change = check)
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'This participant already exists, try repeat this query but do not specify "user_id" field or specify the same value'}, httplib.PRECONDITION_FAILED
    if part == None:            # в том случае если пользователь есть но мы не можем менять атрибуты
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'This participant already exists, try repeat this query but do not specify "user_id" and "descr" fields or specify the same value'}, httplib.PRECONDITION_FAILED

    pstat = get_object_status(part)
    if pstat == 'denied': # пользователь уже был и он запрещен
        return {'code' : PARTICIPANT_DENIED,
                'caption' : 'This participant has denied status, so you can not invite him/her again'}, httplib.PRECONDITION_FAILED

    if part.token == None:      # создаем токен если нету
        part.token = hex4()
        part.save()

    prmt = get_or_create_object_parameter(part, 'status', True, values = [{'value' : a[0], 'caption' : a[1]} for a in Participant.PARTICIPANT_STATUS])
    set_object_parameter(part, user, 'voted', uuid = prmt.uuid)
    set_vote_for_object_parameter(part, user, 'accepted', uuid = prmt.uuid, comment = params.get('comment'))
    # отправляем письмо на электронную почту участника
    site = Site.objects.get_current()
    try:
        send_mail(u'Пользователь {0} пригласил вас на проект на сайте {1}'.format(reguser.name, site.name),
                  u"""вас пригласили на проект на сайт {0}, вот ваш ключ приглашения:
{1}
вы также можете воспользоваться ссылкой для входа в проект
{2}""".format(site.name,
              part.token,
              generate_user_magic_link('invitation', part.token)),
                  settings.EMAIL_HOST_USER,
                  [params['email']])
    except Exception as e:
        print(str(e))
        return {'code'    : EMAIL_CAN_NOT_BE_SENT,
                'caption' : 'Email can not be sent because of {0}'.format(str(e))}, httplib.PRECONDITION_FAILED

    r, st = execute_conform_participant({'psid' : params['psid'],
                                         'uuid' : part.uuid})
    if st == httplib.CREATED:
        return return_if_debug({'token' : part.token}), httplib.CREATED
    else:
        return r, st

@get_user
@get_object_by_uuid(Participant,
                    PARTICIPANT_NOT_FOUND,
                    u'There is no participant with such uuid')
def execute_conform_participant(params, partic, user):
    prj = partic.project
    if prj != user.project:
        return {'code' : ACCESS_DENIED,
                'caption' : 'This participant is not in your project'}, httplib.PRECONDITION_FAILED
    if prj.ruleset == 'despot':
        return despot_conform_participant(user, partic, params)
    else:
        return u'project with ruleset {0} is not supported in conform_participant'.format(prj.ruleset), httplib.NOT_IMPLEMENTED

def despot_conform_participant(voter, prt, params):
    # если мы не имеем предложений по участнику, то выходим

    vt = get_vote_value_for_object_parameter(prt, voter, tpclass = 'status')
    if vt == None:
        return u'There is no one active vote for participant', httplib.CREATED

    if (not voter.is_initiator) and (not ((voter == prt) and (vt.value == 'denied'))):
        return 'You are not initiator, doing nothing', httplib.CREATED
    set_as_accepted_value_of_object_parameter(vt)
    return '', httplib.CREATED


@get_object_by_uuid(Project,
                    PROJECT_NOT_FOUND,
                    u'No such project')
def execute_enter_project_open(params, prj):   #++TESTED
    if params.get('name') == None and params.get('user_id') == None:
        return {'code' : PARAMETERS_BROKEN,
                'caption' : 'You must define at least  `user_id` or `name` parameter'}, httplib.PRECONDITION_FAILED
    if prj.sharing != 'open':
        return {'code' : PROJECT_MUST_BE_OPEN,
                'caption' : 'You can join just to open projects'}, httplib.PRECONDITION_FAILED
    if get_object_status(prj) != 'planning':
        return {'code' : PROJECT_STATUS_MUST_BE_PLANNING,
                'caption' : 'Project status is not "planning"'}, httplib.PRECONDITION_FAILED
    
    prt = Participant(project=prj, dt=datetime.now(),
                      is_initiator=False, psid=hex4(), token=hex4())
    
    if params.get('user_id') != None:
        try:
            u = Participant.objects.filter(token = params['user_id']).all()[0]
        except IndexError:
            try:
                u = User.objects.filter(token = params['user_id']).all()[0]
            except IndexError:
                if params.get('name') == None:
                    return {'code' : USER_NOT_FOUND,
                            'caption' : 'Can not find participant or user'}, httplib.PRECONDITION_FAILED
                else:
                    prt.name = params['name']
                if params.get('descr') != None:
                    prt.descr = params['descr']
            else:
                prt.user = u
                
                if params.get('name') == None:
                    prt.name = u.name
                else:
                    prt.name = params['name']

                if params.get('descr') == None:
                    prt.descr = u.descr
                else:
                    prt.descr = params['descr']
        else:
            u.psid = hex4()
            u.save(force_update=True)
            return {'psid' : u.psid, # u - is an existing participant
                    'token' : u.token}, httplib.CREATED
    else:
        prt.name = params['name']
        if params.get('descr') != None:
            prt.descr = params['descr']
            
    try:
        prt.save(force_insert = True)
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'There is one participant with such name or user_id in this project'}, httplib.PRECONDITION_FAILED
    pprm = create_object_parameter(prt, 'status', True, values = [{'value' : a[0]} for a in Participant.PARTICIPANT_STATUS])
    set_object_status(prt, prt, 'accepted')
    return {'psid' : prt.psid,
            'token' : prt.token}, httplib.CREATED


@get_object_by_uuid(Project,
                    PROJECT_NOT_FOUND,
                    u'There is no such project')
def execute_enter_project_invitation(params, prj):
    try:
        prt = Participant.objects.filter(Q(project=prj) &
                                         (Q(token=params['token']) |
                                          Q(user__token=params['token']))).all()[0]
    except IndexError:
        return {'code' : PARTICIPANT_NOT_FOUND,
                'caption' : 'There is no participants with such token or user_id'}, httplib.PRECONDITION_FAILED
    u = get_registered_user(prt.psid)
    if u != None and (not u.is_active):
        return {'code' : AUTHENTICATION_FAILED,
                'caption' : 'Your account is not activated, proceed activation procedure please'}, httplib.PRECONDITION_FAILED
    if get_object_status(prt) != 'accepted':
        return {'code' : ACCESS_DENIED,
                'caption' : 'You are not allowerd user (not accepted status) to do enter to the project'}, httplib.PRECONDITION_FAILED
    prt.dt = datetime.now()
    prt.psid = hex4()
    prt.save(force_update = True)
    return {'psid' : prt.psid}, httplib.CREATED

@get_user
def execute_exclude_participant(params, user):

    return exclude_participant(params, user)

def exclude_participant(params, user):
    prj = user.project
    part = None
    if params.get('uuid') == None:
        part = user
    else:
        try:
            part = Participant.objects.filter(uuid=params['uuid']).all()[0]
        except IndexError:
            return {'code' : PARTICIPANT_NOT_FOUND,
                    'caption' : 'There is no participant with such uuid'}, httplib.PRECONDITION_FAILED
        if part.project != user.project:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You can not change this participant (wrong project)'}, httplib.PRECONDITION_FAILED

    if get_object_status(part) == 'denied':
        return 'This participant is denied already', httplib.CREATED

    set_vote_for_object_parameter(part, user, 'denied', tpclass = 'status', comment = params.get('comment'))

    # согласуем участника
    return execute_conform_participant({'psid' : params['psid'],
                                        'uuid' : part.uuid})

@get_user
def execute_conform_participant_vote(params, user):
    if params.get('uuid') == None:
        params['uuid'] = user.uuid
        part = user
    else:
        try:
            part = Participant.objects.filter(uuid=params['uuid']).all()[0]
        except IndexError:
            return {'code' : PARTICIPANT_NOT_FOUND,
                    'caption' : 'Participant not found'}, httplib.PRECONDITION_FAILED
    if params['vote'] == 'exclude':
        return exclude_participant(params, user)
    elif get_object_status(part) == 'accepted':
        vts = get_parameter_voter(part, 'voted', 'denied', tpclass = 'status')
        if len(vts) == 0:
            return 'Already denied', httplib.CREATED

    set_vote_for_object_parameter(part, user, 'accepted', tpclass = 'status', comment = params.get('comment'))

    # согласуем участника
    return execute_conform_participant({'psid' : params['psid'],
                                        'uuid' : part.uuid})

def execute_list_activities(params):
    psid = params.get('psid')
    uuid = params.get('uuid')
    user = None
    prj = None
    if psid != None:
        user = get_authorized_user(psid)
        if not isinstance(user, Participant):
            return {'code' : ACCESS_DENIED,
                    'caption' : 'This psid is not acceptable'}, httplib.PRECONDITION_FAILED
        prj = user.project
    else:
        try:
            prj = Project.objects.filter(uuid = uuid).all()[0]
        except IndexError:
            return {'code' : PROJECT_NOT_FOUND,
                    'caption' : 'Project with such uuid is not found'}, httplib.PRECONDITION_FAILED

    ret = []

    if isinstance(user, Participant):
        activityset = prj.activity_set.filter(Q(activityparameter__tpclass='status') &
                                              Q(activityparameter__activityparameterval__status='accepted') &
                                              (Q(activityparameter__activityparameterval__value__in=['voted', 'accepted', 'denied']) |
                                               (Q(activityparameter__activityparameterval__value='created') &
                                                Q(activityparameter__activityparameterval__activityparametervote__voter=user)))).distinct().all()
    else:
        activityset = prj.activity_set.filter(Q(activityparameter__tpclass='status') &
                                              Q(activityparameter__activityparameterval__status='accepted') &
                                              Q(activityparameter__activityparameterval__value__in=['voted', 'accepted', 'denied'])).distinct().all()

    for act in activityset:

        a = {'uuid' : act.uuid,
             'name' : act.name,
             'descr' : act.descr,
             'status' : get_object_status(act)}
        if act.begin_date != None:
            a['begin'] = act.begin_date.isoformat()
        if act.end_date != None:
            a['end'] = act.end_date.isoformat()

        vts = []
        for sts in ActivityParameterVal.objects.filter(Q(status='voted') & Q(value__in=['accepted', 'denied']) &
                                                       Q(parameter__tpclass='status') & Q(parameter__obj=act)).all():
            for vtss in sts.activityparametervote_set.all():
                vts.append({'uuid' : vtss.voter.uuid,
                            'vote' : 'include' if sts.value == 'accepted' else 'exclude',
                            'comment' : vtss.comment,
                            'dt' : vtss.create_date.isoformat()})
        a['votes'] = vts
        if isinstance(user, Participant):
            a['participant'] = ActivityParticipant.objects.filter(Q(participant=user) &
                                                                  Q(activity=act) &
                                                                  Q(activityparticipantparameter__tpclass='status') &
                                                                  Q(activityparticipantparameter__activityparticipantparameterval__status='accepted') &
                                                                  Q(activityparticipantparameter__activityparticipantparameterval__value='accepted')).count() > 0
        else:
            a['participant'] = False
            
        ret.append(a)

    return ret, httplib.OK

@get_user
@get_activity_from_uuid()
def execute_activity_participation(params, act, user):

    iam_creator = get_object_status(act) == 'created' and user in get_parameter_voter(act, 'accepted', 'created', tpclass = 'status')
    if not iam_creator:
        # ap = get_authorized_activity_participant(user, act)
        # if ap == None or ap == False:
        #     return {'code' : ACCESS_DENIED,
        #             'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED
        if get_object_status(act) != 'accepted':
            return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                    'caption' : 'Activity must be accepted join in'}, httplib.PRECONDITION_FAILED
    prj = user.project
    ap = get_or_create_object(ActivityParticipant,
                              {'activity' : act,
                               'participant' : user})

    prmt = get_or_create_object_parameter(ap, 'status', True, values = [{'value' : a[0],
                                                                  'caption' : a[1]} for a in ActivityParticipant.ACTIVITY_PARTICIPANT_STATUS])
    set_vote_for_object_parameter(ap, user, 'accepted' if params['action'] == 'include' else 'denied', uuid = prmt.uuid)

    return conform_activity_participation({'psid' : params['psid'],
                                           'uuid' : params['uuid']}, act, user)

def conform_activity_participation(params, act, user):
    """
    Параметры:

    - `psid`: ключ доступа
    - `uuid`: ид мероприятия

    Выполняет согласование участия участника в мероприятии
    """
    try:
        vtval = get_vote_value_for_object_parameter(ActivityParticipant.objects.filter(Q(participant=user) &
                                                                                       Q(activity=act)).all()[0], user, tpclass='status')
    except IndexError:
        return 'There is no activity participant to conform', httplib.CREATED
    if vtval == None:
        return 'There is nothing to conform', httplib.CREATED

    set_as_accepted_value_of_object_parameter(vtval)
    return 'OK', httplib.CREATED

@get_user
def execute_create_activity(params, user):
    prj = user.project
    begin = string2datetime(params['begin'])
    end = string2datetime(params['end'])
    if end < begin:
        return {'code' : WRONG_DATETIME_PERIOD,
                'caption' : 'Begining must be less then ending of time period in fields "begin" and "end"'}, httplib.PRECONDITION_FAILED
    ac = Activity(project=prj,
                  name=params['name'],
                  begin_date = begin,
                  end_date = end)
    if params.get('descr') != None:
        ac.descr=params['descr']
    try:
        ac.save(force_insert=True)
    except IntegrityError:
        return {'code' : ACTIVITY_ALREADY_EXISTS,
                'caption' : 'Activity with such parameters already exists'}, httplib.PRECONDITION_FAILED
    prmt = create_object_parameter(ac, 'status', True, values = [{'value' : a[0],
                                                                  'caption' : a[1]} for a in Activity.ACTIVITY_STATUS])
    set_object_status(ac, user, 'created', comment = params.get('comment'))

    return {'uuid' : ac.uuid}, httplib.CREATED

@get_user
@get_activity_from_uuid()
def execute_public_activity(params, act, user):
    ast = get_object_status(act)
    if ast == 'accepted':
        vts = get_parameter_voter(act, 'voted', 'denied', tpclass = 'status')
        if len(vts) == 0:
            return 'Already accepted', httplib.CREATED
        else:
            set_vote_for_object_parameter(act, user, 'accepted', tpclass = 'status', comment = params.get('comment'))
            return conform_activity(user, act)
    elif ast == 'voted':
        set_vote_for_object_parameter(act, user, 'accepted', tpclass='status')
        return conform_activity(user, act)

    elif ast == 'denied':
        return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                'caption' : 'This activity is denied'}, httplib.PRECONDITION_FAILED
    elif ast == 'created':
        if ActivityParameterVal.objects.filter(Q(status='accepted') &
                                               Q(value='created') &
                                               Q(parameter__tpclass='status') &
                                               Q(parameter__obj=act) &
                                               Q(activityparametervote__voter=user)).count() > 0: # мы создали мероприятие
            set_object_status(act, user, 'voted', comment = params.get('comment'))
            set_vote_for_object_parameter(act, user, 'accepted', tpclass = 'status')
            return conform_activity(user, act)
        else:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You can not public this activity'}, httplib.PRECONDITION_FAILED
    else:
        return 'Active status of activity is not valid, this is likely error somewhere in a service', httplib.INTERNAL_SERVER_ERROR

@get_user
@get_activity_from_uuid()
def execute_conform_activity(params, act, user):
    return conform_activity(user, act)

def conform_activity(user, act):
    prj = user.project
    if prj.ruleset == 'despot':
        return despot_conform_activity(prj, user, act)
    else:
        return '{0} ruleset is not supported by "conform_activity"'.format(prj.ruleset), httplib.NOT_IMPLEMENTED

def despot_conform_activity(prj, user, activity):
    if not user.is_initiator:
        return 'You are not initiator, can not conform', httplib.CREATED
    astv = get_vote_value_for_object_parameter(activity, user, tpclass = 'status')
    if astv == None:
        return 'No one vote found, nothing to conform', httplib.CREATED
    actstat = get_object_status(activity)
    if actstat == 'voted' and astv.value == 'accepted':
        set_as_accepted_value_of_object_parameter(astv)
        activate_all_activity_resouces(activity, user)
        activate_all_activity_parameters(activity, user)
        return 'Activated and all resources and parameters too', httplib.CREATED
    else:
        set_as_accepted_value_of_object_parameter(astv)
        return 'Status changed', httplib.CREATED

def activate_all_activity_resouces(act, user):
    for ares in act.activityresource_set.filter(Q(activityresourceparameter__tpclass = 'status') &
                                                Q(activityresourceparameter__activityresourceparameterval__status = 'voted') &
                                                Q(activityresourceparameter__activityresourceparameterval__value = 'accepted')).distinct().all():
        set_vote_for_object_parameter(ares, user, 'accepted', tpclass = 'status')
        conform_activity_resource(None, ares, None, act, user)
        for aresparam in ares.activityresourceparameter_set.filter(Q(tpclass = 'user')&
                                                                   Q(activityresourceparameterval__status = 'voted')).distinct().all():
            vtvals = aresparam.activityresourceparameterval_set.filter(status = 'voted').all()
            if len(vtvals) == 1:
                set_vote_for_object_parameter(ares, user, vtvals[0].value, uuid = aresparam.uuid)
                conform_resource_parameter(None, aresparam, user)

def activate_all_activity_parameters(act, user):
    for aparam in act.activityparameter_set.filter(Q(activityparameterval__status = 'voted')).distinct().all():
        vls = aparam.activityparameterval_set.filter(status='voted').all()
        if len(vls) == 1:
            set_vote_for_object_parameter(act, user, vls[0].value, uuid = aparam.uuid)
        conform_activity_parameter(None, aparam, user)

@get_user
@get_activity_from_uuid()
def execute_activity_list_participants(params, act, user):
    if get_object_status(act) != 'accepted':
        return [], httplib.OK
    ret = []
    for p in Participant.objects.filter(Q(activityparticipant__activity=act) &
                                        Q(activityparticipant__activityparticipantparameter__tpclass = 'status') &
                                        Q(activityparticipant__activityparticipantparameter__activityparticipantparameterval__status='accepted') &
                                        Q(activityparticipant__activityparticipantparameter__activityparticipantparameterval__value='accepted')).distinct().all():
        ret.append(p.uuid)
    return ret, httplib.OK

@get_user
@get_activity_from_uuid()
def execute_activity_delete(params, act, user):
    # if stat != 'created' or st.activityvote_set.filter(voter=user).count() == 0: # не тот статус или создали не мы
    if ActivityParameterVal.objects.filter(Q(status='accepted') &
                                           Q(value='created') &
                                           Q(activityparametervote__voter=user) &
                                           Q(parameter__tpclass='status') &
                                           Q(parameter__obj=act)).count() == 0:
        return {'code' : ACCESS_DENIED,
                'caption' : 'You can not delete this activity'}, httplib.PRECONDITION_FAILED
    act.delete()
    return 'Deleted', httplib.CREATED

@get_user
@get_activity_from_uuid()
def execute_activity_deny(params, act, user):
    ast = get_object_status(act)
    if ast == 'denied':
        return 'Already denied', httplib.CREATED
    elif ast in ['accepted', 'voted']:
        set_vote_for_object_parameter(act, user, 'denied', tpclass = 'status', comment=params.get('comment'))
        return conform_activity(user, act)
    else:
        return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                'caption' : 'Activity is not even voted, you can not deny it, use "/activity/delete" if you want delete the activity'}, httplib.PRECONDITION_FAILED

@get_user
@get_activity_from_uuid()
def execute_create_activity_parameter(params, act, user):
    if 'default' in params:
        del params['default']
    return create_activity_parameter(params, act, user)

def create_activity_parameter(params, act, user):
    tp = 'text' if params.get('tp') == None else params['tp']
    values = [] if params.get('values') == None else params['values']
    try:
        ap = create_object_parameter(act, 'user', False, tp = tp, name = params['name'],
                                     descr = params.get('descr'), values = values)
    except IntegrityError:
        return {'code' : ACTIVITY_PARAMETER_ALREADY_EXISTS,
                'caption' : 'Parameter with such name is already exists'}, httplib.PRECONDITION_FAILED

    if params.get('value') != None:
        ret, st = change_activity_parameter(params, ap, user)
        if st != httplib.CREATED:
            return ret, st

    return {'uuid' : ap.uuid}, httplib.CREATED

@get_user
@get_activity_from_uuid()
def execute_create_activity_parameter_from_default(params, act, user):
    try:
        dp = DefaultParameter.objects.filter(uuid=params['default']).all()[0]
    except IndexError:
        return {'code': DEFAULT_PARAMETER_NOT_FOUND,
                'caption' : 'There is no such default parameter'}, httplib.PRECONDITION_FAILED

    params['name'] = dp.name    #  FIXME: пока работает но лучше использовать create_object_parameter_from_default
    params['descr'] = dp.descr
    params['tp'] = dp.tp
    params['enum'] = dp.enum
    if params['enum']:
        vs = []
        for v in dp.defaultparametervl_set.all():
            vs.append({'value' : v.value,
                       'caption' : v.caption})
        params['values'] = vs

    return create_activity_parameter(params, act, user)

@get_user
@get_activity_from_uuid()
def execute_list_activity_parameters(params, act, user):
    ret = []
    for prm in act.activityparameter_set.filter(Q(tpclass='user')).all():
       a = {'uuid' : prm.uuid,
            'name' : prm.name,
            'tp' : prm.tp,
            'enum' : prm.enum}
       if prm.descr != None:
           a['descr'] = prm.descr

       vts = []
       for pval in prm.activityparameterval_set.filter(status='voted').all():
           for ptsp in ActivityParameterVote.objects.filter(parameter_val=pval).distinct().all():
               vv = {'uuid' : ptsp.voter.uuid,
                     'value' : pval.value}
               if pval.caption != None:
                   vv['caption'] = pval.caption
               if ptsp.comment != None:
                   vv['comment'] = ptsp.comment
               vts.append(vv)

       a['votes'] = vts

       if prm.enum:
           vls = []
           for vl in prm.activityparametervl_set.all():
               vx = {'value' : vl.value}
               if vl.caption != None:
                   vx['caption'] = vl.caption
           a['values'] = vls

       try:
           aps = prm.activityparameterval_set.filter(status='accepted').all()[0]
           a['value'] = aps.value
           if aps.caption != None:
               a['caption'] = aps.caption
           else:
               a['caption'] = None
       except IndexError:
           a['value'] = None
           a['caption'] = None


       ret.append(a)

    return ret, httplib.OK


@get_user
@get_activity_parameter_from_uuid
def execute_change_activity_parameter(params, ap, user):
    return change_activity_parameter(params, ap, user)


def change_activity_parameter(params, ap, user):
    if ap.activityparameterval_set.filter(Q(status='accepted') & Q(value=params['value'])).count() > 0:
        return 'Already have this value', httplib.CREATED
    try:
        set_vote_for_object_parameter(ap.obj, user, params['value'], uuid=ap.uuid)
    except ValueError:
        return {'code' : ACTIVITY_PARAMETER_ERROR,
                'caption' : 'This value can not be set for enum parameter'}, httplib.PRECONDITION_FAILED
    return conform_activity_parameter(params, ap, user)

@get_user
@get_activity_parameter_from_uuid
def execute_conform_activity_parameter(params, ap, user):
    conform_activity_parameter(params, ap, user)

def conform_activity_parameter(params, ap, user):
    act = ap.obj
    iam_creator = am_i_creating_activity_now(act, user)
    if iam_creator:
        return 'Activity status is "created" so just create an offer', httplib.CREATED
    prj = user.project
    if prj.ruleset == 'despot' :
        return despot_conform_activity_parameter(params, ap, user)
    else:
        return 'Can not conform activity parameter in this project for now', httplib.NOT_IMPLEMENTED

def despot_conform_activity_parameter(params, ap, user):
    if not user.is_initiator:
        return 'You are not initiator, just ignore', httplib.CREATED
    return just_change_activity_parameter(params, ap, user)

def just_change_activity_parameter(params, ap, user):
    apvt = get_vote_value_for_object_parameter(ap.obj, user, uuid=ap.uuid)
    if apvt == None:
        return 'Nothing to conform', httplib.CREATED
    set_as_accepted_value_of_object_parameter(apvt)
    return 'Value changed', httplib.CREATED


@get_user
def execute_create_project_resource(params, user):
    u = get_or_create_object(MeasureUnits, {'name' : params['units']})
    prj = user.project
    res = Resource(project = prj,
                   name=params['name'],
                   measure = u,
                   usage = params['use'],
                   site = params['site'])
    if isinstance(params.get('descr'), basestring):
        res.descr = params['descr']
    try:
        res.save(force_insert=True)
    except IntegrityError:
        return {'code' : RESOURCE_ALREADY_EXISTS,
                'caption' : 'Resource with such name is already exists'}, httplib.PRECONDITION_FAILED
    return {'uuid' : res.uuid}, httplib.CREATED

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
def execute_include_personal_resource(params, actres, resource, act, user):
    if resource.usage != 'personal' :
        return {'code' : RESOURCE_WRONG_USAGE,
                'caption' : 'You can not use common resource as personal'}, httplib.PRECONDITION_FAILED
    ap = get_authorized_activity_participant(user, act)
    if ap == None or ap == False:
        return {'code' : ACCESS_DENIED,
                'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED
    if params['amount'] > 0.001:
        get_or_create_object(ParticipantResource, {'resource' : actres,
                                                   'participant' : ap},
                             {'amount' : params['amount']})
        return 'Created', httplib.CREATED
    else:
        ParticipantResource.objects.filter(resource = actres, participant = ap).delete()
        return 'Deleted', httplib.CREATED

# @get_user
def execute_list_activity_resources(params):
    user = None
    if params.get('psid') != None:
        user = get_authorized_user(params['psid'])
        if user == None:
            return {'code' : PARTICIPANT_NOT_FOUND,
                    'caption' : 'Participant is not found'}, httplib.PRECONDITION_FAILED
        elif user == False:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'Participant is not allowed'}, httplib.PRECONDITION_FAILED
        proj = user.project
    elif params.get('project') != None:
        try:
            proj = Project.objects.filter(uuid = params['project']).all()[0]
        except IndexError:
            return {'code' : PROJECT_NOT_FOUND,
                    'caption' : 'Project not found'}, httplib.PRECONDITION_FAILED
        if proj.sharing != 'open':
            return {'code' : PROJECT_MUST_BE_OPEN,
                    'caption' : 'Project must be open'}, httplib.PRECONDITION_FAILED
    else:
        return {'code' : PARAMETERS_BROKEN,
                'caption' : 'Must be declared at least `project` or `psid`'}, httplib.PRECONDITION_FAILED
    
    if isinstance(params.get('uuid'), basestring):
        return list_activity_resources(params, user, proj)
    else:
        return list_project_resources(params, proj)

# @get_activity_from_uuid()
def list_activity_resources(params, user, proj):
    try:
        act = Activity.objects.filter(Q(project = proj) & Q(uuid = params['uuid'])).all()[0]
    except IndexError:
        return {'code' : ACTIVITY_NOT_FOUND,
                'caption' : 'Activity not found'}, httplib.PRECONDITION_FAILED
    
    
    ret = []
    for ar in act.activityresource_set.all():
        res = ar.resource
        stt = get_object_status(ar)
        p = {'uuid' : res.uuid,
             'name' : res.name,
             'product' : res.product,
             'descr' : res.descr,
             'units' : res.measure.name,
             'status' : stt if stt != None else 'voted',
             'min_cost' : float(res.min_cost) if res.min_cost != None else None,
             'max_cost' : float(res.max_cost) if res.max_cost != None else None,
             'mean_cost' : float(res.mean_cost) if res.mean_cost != None else None,
             'min_cost_sum' : None,
             'max_cost_sum' : None,
             'mean_cost_sum' : None,
             'use' : res.usage,
             'site' : res.site}


        vts = []
        for vt in ActivityResourceParameterVote.objects.filter(Q(parameter_val__parameter__obj = ar) &
                                                               Q(parameter_val__parameter__tpclass = 'status') &
                                                               Q(parameter_val__status = 'voted')).distinct().all():
            vts.append({'uuid' : vt.voter.uuid,
                        'vote' : 'include' if vt.parameter_val.value == 'accepted' else 'exclude',
                        'comment' : vt.comment,
                        'dt' : vt.create_date.isoformat()})
        p['votes'] = vts
        if res.usage == 'common':
            p['used'] = p['status'] == 'accepted'
            p['amount'] = float(ar.amount)
        else:
            p['used'] = False
            p['amount'] = 0
            apar = None
            if user != None:
                apar = get_authorized_activity_participant(user, act)
            if isinstance(apar, ActivityParticipant):
                try:
                    pres = ar.participantresource_set.filter(participant=apar).distinct().all()[0]
                    p['used'] = True
                    p['amount'] = float(pres.amount)
                except IndexError:
                    pass
        p['contractors'] = []
        p['cost'] = None

        ret.append(p)
    return ret, httplib.OK

def get_full_resource_amount(res):
    if res.usage == 'common':
        x = res.activityresource_set.filter(Q(activityresourceparameter__tpclass = 'status')&
                                            Q(activityresourceparameter__activityresourceparameterval__status = 'accepted')&
                                            Q(activityresourceparameter__activityresourceparameterval__value = 'accepted')&
                                            Q(activity__activityparameter__tpclass = 'status') &
                                            Q(activity__activityparameter__activityparameterval__status = 'accepted')&
                                            Q(activity__activityparameter__activityparameterval__value = 'accepted')).aggregate(Sum('amount'))
        return float(x['amount__sum']) if x['amount__sum'] != None else 0
    else:
        x = ParticipantResource.objects.filter(Q(resource__resource=res)&
                                               Q(resource__activityresourceparameter__tpclass = 'status')&
                                               Q(resource__activityresourceparameter__activityresourceparameterval__status = 'accepted')&
                                               Q(resource__activityresourceparameter__activityresourceparameterval__value = 'accepted')&
                                               Q(participant__activity__activityparameter__tpclass = 'status') &
                                               Q(participant__activity__activityparameter__activityparameterval__status = 'accepted')&
                                               Q(participant__activity__activityparameter__activityparameterval__value = 'accepted')).aggregate(Sum('amount'))
        return float(x['amount__sum']) if x['amount__sum'] != None else 0


def list_project_resources(params, prj):
    # prj = user.project
    ret = []
    for res in prj.resource_set.all():
        p = {'uuid' : res.uuid,
             'name' : res.name,
             'product' : res.product,
             'descr' : res.descr,
             'units' : res.measure.name,
             'status' : 'accepted',
             'min_cost' : float(res.min_cost) if res.min_cost != None else None,
             'max_cost' : float(res.max_cost) if res.max_cost != None else None,
             'mean_cost' : float(res.mean_cost) if res.mean_cost != None else None,
             'use' : res.usage,
             'site' : res.site,
             'votes' : []}
        q = (Q(activityresourceparameter__tpclass='status')&
             Q(activityresourceparameter__activityresourceparameterval__status = 'accepted')&
             Q(activityresourceparameter__activityresourceparameterval__value = 'accepted'))
        if res.usage == 'personal':
            q &= Q(participantresource__amount__gt = 0)
        p['used'] = res.activityresource_set.filter(q).count() > 0
        p['amount'] = get_full_resource_amount(res)

        cnt = []
        for c in Contractor.objects.filter(Q(contractoroffer__resource = res)).distinct().all():
            cc = {'name' : c.name,
                  'user' : c.user_id}
            try:
                cof = c.contractoroffer_set.filter(resource = res).all()[0]
            except IndexError:
                pass
            else:
                cc['cost'] = float(cof.cost)
                cc['offer_amount'] = float(cof.amount) if cof.amount != None else None # если поставщик не предложил ничего
                try:
                    cus = c.contractorusage_set.filter(resource = res).all()[0]
                except IndexError:
                    cc['amount'] = 0
                    cc['votes'] = []
                else:
                    v = get_object_parameter(cus, 'amount')
                    cc['amount'] = float(v) if v != None else 0
                    vts = []
                    for pp in ContractorUsagePrmtVote.objects.filter(Q(parameter_val__status = 'voted')&
                                                                     Q(parameter_val__parameter__tpclass = 'amount')&
                                                                     Q(parameter_val__parameter__obj=cus)).distinct().all():
                        vts.append({'uuid' : pp.voter.uuid,
                                    'amount' : float(pp.parameter_val.value)})
                    cc['votes'] = vts
                cnt.append(cc)
        p['contractors'] = cnt
        p['cost'] = sum([x['cost'] * x['amount'] if (x['cost'] != None and x['amount'] != None) else 0 for x in cnt])
        p['available'] = sum([x['amount'] if x['amount'] != None else 0 for x in cnt])
        p['min_cost_sum'] = float(res.min_cost) * p['amount'] if res.min_cost != None else None
        p['max_cost_sum'] = float(res.max_cost) * p['amount'] if res.max_cost != None else None
        p['mean_cost_sum'] = float(res.mean_cost) * p['amount'] if res.mean_cost != None else None
        ret.append(p)
    return ret, httplib.OK


@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
def execute_include_activity_resource(params, res, act, user):
    iam_creator = am_i_creating_activity_now(act, user)
    if not iam_creator:
        ap = get_authorized_activity_participant(user, act)
        if ap == None or ap == False:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED

    try:
        ap = ActivityResource.objects.filter(resource = res, activity = act).all()[0]
    except IndexError:
        ap = ActivityResource(resource = res,
                              activity = act,
                              required = params['need'] if res.usage == 'common' else False,
                              amount = params['amount'] if res.usage == 'common' else False )
        ap.save(force_insert=True)
        p = create_object_parameter(ap, 'status', True, values = [{'value' : a[0],
                                                                   'caption' : a[1]} for a in ActivityResource.ACTIVITY_RESOURCE_STATUS])
        set_object_parameter(ap, user, 'voted', uuid = p.uuid)
        set_vote_for_object_parameter(ap, user, 'accepted', uuid = p.uuid,
                                      comment = params.get('comment'))
        return conform_activity_resource(params, ap, res, act, user)

    st = get_object_status(ap)
    if st == 'accepted':
        vts = get_parameter_voter(ap, 'voted', 'denied', tpclass = 'status')
        if len(vts) == 0:
            return "Has already", httplib.CREATED
    elif st == 'denied':
        if not iam_creator:
            return {'code' : ACTIVITY_RESOURCE_IS_NOT_ACCEPTED,
                    'caption' : 'This resource is denied on this activity'}, httplib.PRECONDITION_FAILED
    set_vote_for_object_parameter(ap, user, 'accepted', tpclass = 'status',
                                  comment = params.get('comment'))
    return conform_activity_resource(params, ap, res, act, user)

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
def execute_exclude_activity_resource(params, res, act, user):
    if not (get_object_status(act) == 'created' and (user in get_parameter_voter(act, 'accepted', 'created', tpclass = 'status'))):
        ap = get_authorized_activity_participant(user, act)
        if ap == None or ap == False:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED
    try:
        ap = ActivityResource.objects.filter(resource = res, activity = act).all()[0]
    except IndexError:
        return "Already excluded", httplib.CREATED

    st = get_object_status(ap)
    if st == 'denied':
        return "Already denied", httplib.CREATED
    set_vote_for_object_parameter(ap, user, 'denied', tpclass = 'status',
                                  comment = params.get('comment'))
    return conform_activity_resource(params, ap, res, act, user)


@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
def execute_conform_activity_resource(params, actres, res, act, user):
    conform_activity_resource(params, actres, res, act, user)

def conform_activity_resource(params, actres, res, act, user):
    prj = user.project
    if prj.ruleset == 'despot':
        return despot_conform_activity_resource(params, actres, res, act, user)
    else:
        return 'conform activity resource is not implemented for project ruleset {0}'.format(prj.ruleset), httplib.NOT_IMPLEMENTED

def despot_conform_activity_resource(params, actres, res, act, user):
    iam_creator = get_object_status(act) == 'created' and user in get_parameter_voter(act, 'accepted', 'created', tpclass = 'status')
    if iam_creator:
        return 'Status of this activity is "created" so you just offer resources', httplib.CREATED
    if get_object_status(act) != "accepted":
        return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                'caption' : 'This activity is not "accepted"'}, httplib.PRECONDITION_FAILED
    if not user.is_initiator:
        return 'You are not initiator, ignore', httplib.CREATED

    st = get_object_status(actres)
    if st == 'denied':
        return {'code' : ACTIVITY_RESOURCE_IS_NOT_ACCEPTED,
                'caption' : 'This resource is denied on the activity'}, httplib.PRECONDITION_FAILED

    vtval = get_vote_value_for_object_parameter(actres, user, tpclass = 'status')
    set_as_accepted_value_of_object_parameter(vtval)
    return "Created", httplib.CREATED


@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
def execute_create_resource_parameter(params, ares, res, act, user):
    apar = get_authorized_activity_participant(user, act)
    if apar == None or apar == False:
        return {'code' : ACCESS_DENIED,
                'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED
    if res.usage == 'common':
        return create_common_resource_parameter(params, ares, res, apar, act, user)
    else:
        return create_personal_resource_parameter(params, ares, res, apar, act, user)

def create_common_resource_parameter(params, ares, res, apar, act, user):
    # import pudb
    # pudb.set_trace()
    try:
        prm = create_object_parameter(ares, 'user', False, tp = params['tp'],
                                      name = params['name'], descr = params.get('descr'),
                                      values = params.get('values') if params['enum'] else [])
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exist'}, httplib.PRECONDITION_FAILED

    if isinstance(params.get('value'), basestring):
        ret, st =  change_resource_parameter(params, prm, user)
        if st != httplib.CREATED:
            return ret, st
    return {'uuid' : prm.uuid}, httplib.CREATED

def create_personal_resource_parameter(params, ares, res, apar, act, user):
    try:
        pres = ares.participantresource_set.filter(participant = apar).all()[0]
    except IndexError:
        return {'code' : PERSONAL_RESOURCE_NOT_FOUND,
                'caption' : 'You are not using this resource'}, httplib.PRECONDITION_FAILED
    try:
        prm = create_object_parameter(pres, 'user', False, tp = params['tp'],
                                      name = params['name'], descr = params.get('descr'),
                                      values = params.get('values') if params['enum'] else [])
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exists'}, httplib.PRECONDITION_FAILED
    if isinstance(params.get('value'), basestring):
        set_object_parameter(pres, user, params['value'], uuid = prm.uuid,
                             caption = params['caption'], comment = params['comment'])
    return {'uuid' : prm.uuid}, httplib.CREATED

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
def execute_create_resource_parameter_from_default(params, ares, res, act, user):
    apar = get_authorized_activity_participant(user, act)
    if apar == None or apar == False:
        return {'code' : ACCESS_DENIED,
                'caption' : 'You are not activity participant'}, httplib.PRECONDITION_FAILED
    try:
        default = DefaultParameter.objects.filter(uuid=params['default']).all()[0]
    except IndexError:
        return {'code' : DEFAULT_PARAMETER_NOT_FOUND,
                'caption' : 'There is no such default parameter'}, httplib.PRECONDITION_FAILED

    if res.usage == 'common':
        return create_common_resource_parameter_from_default(params, default, ares, res, act, user)
    else:
        return create_personal_resource_parameter_from_default(params, default, ares, res, apar, act, user)

def create_common_resource_parameter_from_default(params, default, ares, res, act, user):
    try:
        prm = create_object_parameter_from_default(ares, default)
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exists'}, httplib.PRECONDITION_FAILED
    if default.default_value != None:
        params['value'] = default.default_value
        ret, st = change_resource_parameter(params, prm, user)
        if st != httplib.CREATED:
            return ret, st
    return {'uuid' : prm.uuid}, httplib.CREATED

def create_personal_resource_parameter_from_default(params, default, ares, res, apar, act, user):
    try:
        aprtres = apar.participantresource_set.filter(resource=ares).all()[0]
    except IndexError:
        return {'code' : PERSONAL_RESOURCE_NOT_FOUND,
                'caption' : 'You are not using this resource now'}, httplib.PRECONDITION_FAILED
    try:
        prmt = create_object_parameter_from_default(aprtres, default)
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This resource parameter is already exists'}
    if default.default_value != None:
        set_object_parameter(aprtres, user, params['value'], uuid = prmt)
    return {'uuid' : prmt.uuid}, httplib.CREATED


@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
def execute_list_activity_resource_parameters(params, ares, res, act, user):
    if res.usage == 'common':
        return list_common_activity_resource_parameters(params, ares, res, act, user)
    else:
        return list_personal_activity_resource_parameters(params, ares, res, act, user)

def list_personal_activity_resource_parameters(params, ares, res, act, user):
    apar = get_authorized_activity_participant(user, act)
    if apar == None or apar == False:
        return [], httplib.OK
    try:
        pres = apar.participantresource_set.filter(resource = ares).all()[0]
    except IndexError:
        return [], httplib.OK
    ret = []
    for prmt in pres.participantresourceparameter_set.filter(tpclass = 'user').all():
        p = {'uuid' : prmt.uuid,
             'name' : prmt.name,
             'descr' : prmt.descr,
             'tp' : prmt.tp,
             'enum' : prmt.enum}
        vls = []
        for vl in prmt.participantresourceparametervl_set.all():
            vls.append({'value' : vl.value,
                        'caption' : vl.caption})
        p['values'] = vls
        try:
            vl = prmt.participantresourceparameterval_set.filter(status = 'accepted').all()[0]
        except IndexError:
            p['value'] = None
            p['caption'] = None
        else:
            p['value'] = vl.value
            p['caption'] = vl.caption
        p['votes'] = []
        ret.append(p)
    return ret, httplib.OK


def list_common_activity_resource_parameters(params, ares, res, act, user):
    ret = []
    for prmt in ares.activityresourceparameter_set.filter(tpclass = 'user').all():
        p = {'uuid' : prmt.uuid,
             'name' : prmt.name,
             'descr' : prmt.descr,
             'tp' : prmt.tp,
             'enum' : prmt.enum}
        if prmt.enum:
            vls = []
            for vl in prmt.activityresourceparametervl_set.all():
                vls.append({'value' : vl.value,
                            'caption' : vl.caption})
            p['values'] = vls
        else:
            p['values'] = []
        try:
            val = prmt.activityresourceparameterval_set.filter(status='accepted').all()[0]
        except IndexError:
            p['value'] = None
            p['caption'] = None
        else:
            p['value'] = val.value
            p['caption'] = val.caption
        vts = []
        for pval in prmt.activityresourceparameterval_set.filter(status='voted').all():
            for vote in pval.activityresourceparametervote_set.all():
                vts.append({'uuid' : vote.voter.uuid,
                            'value' : pval.value,
                            'caption' : pval.caption,
                            'comment' : vote.comment,
                            'dt' : vote.create_date.isoformat()})
        p['votes'] = vts
        ret.append(p)
    return ret, httplib.OK

@get_user
@get_resource_parameter_from_uuid()
def execute_change_resource_parameter(params, resp , user):
    return change_resource_parameter(params, resp, user)


def change_resource_parameter(params, aresp, user):
    if isinstance(aresp, ActivityResourceParameter):
        return change_common_resource_parameter(params, aresp, user)
    elif isinstance(aresp, ParticipantResourceParameter):
        return change_personal_resouce_parameter(params, aresp, user)
    else:
        return 'Tryed to change resource parameter of wrong type {0}'.format(type(aresp)), httplib.INTERNAL_SERVER_ERROR

def change_common_resource_parameter(params, aresp, user):
    ares = aresp.obj
    # import pudb
    # pudb.set_trace()
    set_vote_for_object_parameter(ares,
                                  user,
                                  params['value'],
                                  uuid=aresp.uuid,
                                  comment = params.get('comment'),
                                  caption = params.get('caption'))
    return conform_resource_parameter(params, aresp, user)

def change_personal_resouce_parameter(params, aresp, user):
    pres = aresp.obj
    set_object_parameter(pres, user, params['value'], uuid = aresp.uuid,
                         caption = params.get('caption'), comment = params.get('comment'))
    return 'Created', httplib.CREATED

@get_user
@get_resource_parameter_from_uuid()
def execute_conform_resource_parameter(params, aresp, user):
    return conform_resource_parameter(params, aresp, user)

def conform_resource_parameter(params, aresp, user):
    prj = user.project
    if prj.ruleset == 'despot':
        return despot_conform_resource_parameter(params, aresp, user)
    else:
        return 'Conform parmameter is not implemented for project ruleset {0}'.format(prj.ruleset), httplib.NOT_IMPLEMENTED


def despot_conform_resource_parameter(params, aresp, user):
    if not user.is_initiator:
        return 'Not initiator - ignore', httplib.CREATED
    vtv = get_vote_value_for_object_parameter(aresp.obj, user, uuid = aresp.uuid)
    if vtv == None:
        return 'Nothing to conform', httplib.PRECONDITION_FAILED
    set_as_accepted_value_of_object_parameter(vtv)
    return 'Created', httplib.CREATED

def execute_create_contractor(params):
    c = Contractor(name = params['user'],
                   user_id = params['user'])
    try:
        c.save(force_insert=True)
    except IntegrityError:
        return {'code' : CONTRACTOR_ALREADY_EXISTS,
                'caption' : 'There is at least one contractor with such name or user_id exists'}, httplib.PRECONDITION_FAILED
    if params.get('contacts') != None:
        for cnt in params['contacts']:
            cc = ContractorContact(contractor = c,
                                   tp = cnt['type'],
                                   value = cnt['value'])
            try:
                cc.save(force_insert=True)
            except IntegrityError:
                pass
    return 'Created', httplib.CREATED

@get_user
def execute_use_contractor(params, user):
    prj = user.project
    if get_object_status(prj) != 'contractor':
        return {'code' : PROJECT_STATUS_MUST_BE_CONTRACTOR,
                'caption' : 'Project status must be "contractor" for this'}, httplib.PRECONDITION_FAILED
    try:
        res = Resource.objects.filter(uuid=params['resource']).all()[0]
    except IndexError:
        return {'code' : RESOURCE_NOT_FOUND,
                'caption' : 'There is no such resource'}, httplib.PRECONDITION_FAILED
    try:
        cnt = Contractor.objects.filter(user_id=params['contractor']).all()[0]
    except IndexError:
        return {'code' : CONTRACTOR_NOT_FOUND,
                'caption' : 'There is no contractor with such user_id'}, httplib.PRECONDITION_FAILED
    try:
        off = ContractorOffer.objects.filter(Q(contractor=cnt) & Q(resource = res)).all()[0]
    except IndexError:
        return {'code' : RESOURCE_IS_NOT_OFFERED,
                'caption' : 'This contractor does not offer this resource'}, httplib.PRECONDITION_FAILED
    allowerd = get_full_resource_amount(res) - get_full_resource_available(res)
    if params.get('amount') == None:
        am = allowerd
    else:
        am = min(allowerd, params['amount'])
    if off.amount != None:
        am = min(am, off.amount)
    try:
        cntu = ContractorUsage.objects.filter(Q(contractor = cnt) & Q(resource = res)).all()[0]
    except IndexError:
        if am < 0.001:
            return 'Not using already', httplib.CREATED
        else:
            cntu = ContractorUsage(contractor = cnt, resource = res)
            cntu.save(force_insert=True)
    prmt = get_or_create_object_parameter(cntu, 'amount', True, descr = 'amount of resource to use with contractor')
    set_vote_for_object_parameter(cntu, user, am, uuid = prmt.uuid)
    return conform_use_contractor(params, cntu, res, user)

def conform_use_contractor(params, cntu, res, user):
    prj = user.project
    if prj.ruleset == 'despot' :
        return despot_conform_use_contractor(params, cntu, res, user)
    else:
        return 'Conform contractor usage is not implemented for project ruleset = {0}'.format(prj.ruleset), httplib.NOT_IMPLEMENTED

def despot_conform_use_contractor(params, cntu, res, user):
    if not user.is_initiator:
        return 'You are not initiator, ignore conforming', httplib.CREATED
    vt = get_vote_value_for_object_parameter(cntu, user, tpclass = 'amount')
    if vt == None:
        return 'Nothing to conform', httplib.CREATED
    am = float(vt.value)
    if am < 0.001:
        cntu.delete()
    else:
        set_as_accepted_value_of_object_parameter(vt)
    return 'Created', httplib.CREATED

# @get_user
# def execute_report_project_statistics(params, user):
#     prj = user.project
#     ret = {'uuid' : prj.uuid,
#            'name' : prj.name,
#            'descr' : prj.descr,
#            'sharing' : prj.sharing,
#            'ruleset' : prj.ruleset,
#            'begin_date' : prj.begin_date.isoformat(),
#            'end_date' : prj.end_date.isoformat()}
#     res = []
#     for res in prj.resource_set.all():
#         p = {'uuid' : res.uuid,
#              'product' : res.product,
#              'amount' : get_full_resource_amount(res),
#              'available' : get_full_resource_available(res),
#              'cost' : get_full_resource_cost(res),
#              'name' : res.name,
#              'descr' : res.descr,
#              'units' : res.measure.name,
#              'use' : res.usage,
#              'site' : res.site}
#         res.append(p)
#     ret['resources'] = res
#     ret['cost'] = sum([a['cost'] for a in res])
#     return ret, httplib.OK


# @get_user
# def execute_activity_statistics(params, user):
#     pass

@get_user
def execute_participant_statistics(params, user):
    prts = []
    prj = user.project
    if params.get('uuids') == None or len(params['uuids']) == 0:
        qry = prj.participant_set.filter(Q(participantparameter__tpclass = 'status')&
                                         Q(participantparameter__participantparameterval__status = 'accepted')&
                                         Q(participantparameter__participantparameterval__value = 'accepted')).distinct().all()
    else:
        qry = prj.participant_set.filter(uuid_in = params['uuids']).distinct().all()
    queryres = prj.resource_set.all()
    for part in qry:
        pstat = get_object_status(part)
        p = {'uuid' : part.uuid,
             'create' : part.create_date.isoformat(),
             'login' : part.dt.isoformat() if part.dt != None else None,
             'is_initiator' : part.is_initiator,
             'user_id' : part.user,
             'name' : part.name,
             'descr' : part.descr,
             'status' : pstat}
        resources = []
        for res in queryres:
            if res.usage == 'common':
                rst = get_participant_common_resource_stats(part, res)
            else:
                rst = get_participant_personal_resouce_stats(part, res)
            if rst != None:
                resources.append(rst)
        p['resources'] = resources
        p['cost'] = sum([a['cost'] for a in resources])
        prts.append(p)
    ret = {}
    ret['participants'] = prts
    ret['cost'] = sum([a['cost'] for a in prts])
    resources = {}
    for part in prts:
        for res in part['resources']:
            if res['uuid'] not in resources:
                resources[res['uuid']] = copy(res)
            else:
                oldres = resources[res['uuid']]
                for n in ['amount', 'available', 'cost',
                          'min_cost', 'max_cost', 'mean_cost']:
                    if res[n] != None:
                        oldres[n] = oldres[n] + res[n] if oldres[n] != None else res[n]
                resources[res['uuid']] = oldres
    ret['resources'] = [val for val in resources.itervalues()]
    micost = sum([a['min_cost'] if a['min_cost'] != None else 0 for a in ret['resources']])
    ret['min_cost'] = micost if micost > 0 else None
    macost = sum([a['max_cost'] if a['max_cost'] != None else 0 for a in ret['resources']])
    ret['max_cost'] = macost if macost > 0 else None
    meacost = sum([a['mean_cost'] if a['mean_cost'] != None else 0  for a in ret['resources']])
    ret['mean_cost'] = meacost if meacost > 0 else None
    return ret, httplib.OK


def get_participant_common_resource_stats(part, res):
    ares = res.activityresource_set.filter(Q(activity__activityparameter__tpclass = 'status') &
                                           Q(activity__activityparameter__activityparameterval__status = 'accepted')&
                                           Q(activity__activityparameter__activityparameterval__value = 'accepted')&
                                           Q(activity__activityparticipant__activityparticipantparameter__tpclass = 'status') &
                                           Q(activity__activityparticipant__activityparticipantparameter__activityparticipantparameterval__status = 'accepted') &
                                           Q(activity__activityparticipant__activityparticipantparameter__activityparticipantparameterval__value = 'accepted')&
                                           Q(activityresourceparameter__tpclass='status')&
                                           Q(activityresourceparameter__activityresourceparameterval__status = 'accepted')&
                                           Q(activityresourceparameter__activityresourceparameterval__value = 'accepted')&
                                           Q(activity__activityparticipant__participant = part)).distinct()
    if ares.count() == 0:
        return None
    amount = 0
    for ar in ares.all():
        apars = ar.activity.activityparticipant_set.filter(Q(activityparticipantparameter__tpclass = 'status')&
                                                           Q(activityparticipantparameter__activityparticipantparameterval__status = 'accepted')&
                                                           Q(activityparticipantparameter__activityparticipantparameterval__value = 'accepted')).count()
        try:
            a = float(ar.amount) / float(apars)
        except ZeroDivisionError:
            a = 0
        amount += a
    fullamount = get_full_resource_amount(res)
    fullavailable = get_full_resource_available(res)
    try:
        available = amount * fullavailable / fullamount
    except ZeroDivisionError:
        available = 0
    try:
        cost = get_full_resource_cost(res) * available / fullavailable
    except ZeroDivisionError:
        cost = 0
    ret = {'uuid' : res.uuid,
           'product' : res.product,
           'amount' : amount,
           'available' : available,
           'cost' : cost,
           'min_cost' : float(res.min_cost) * amount if res.min_cost != None else None,
           'max_cost' : float(res.max_cost) * amount if res.max_cost != None else None,
           'mean_cost' : float(res.mean_cost) * amount if res.mean_cost != None else None,
           'name' : res.name,
           'descr' : res.descr,
           'units' : res.measure.name,
           'use' : res.usage,
           'site' : res.site}
    return ret

def get_full_resource_cost(res):
    ret = 0
    for usg in res.contractorusage_set.all():
        try:
            off = res.contractoroffer_set.filter(contractor = usg.contractor).all()[0]
        except IndexError:
            continue
        prmt = get_object_parameter(usg, tpclass = 'amount')
        if prmt != None:
            amount = float(prmt)
            ret += amount * float(off.cost)
    return ret


def get_participant_personal_resouce_stats(part, res):
    ares = res.activityresource_set.filter(Q(activity__activityparameter__tpclass = 'status') &
                                           Q(activity__activityparameter__activityparameterval__status = 'accepted')&
                                           Q(activity__activityparameter__activityparameterval__value = 'accepted')&
                                           Q(activity__activityparticipant__activityparticipantparameter__tpclass = 'status') &
                                           Q(activity__activityparticipant__activityparticipantparameter__activityparticipantparameterval__status = 'accepted') &
                                           Q(activity__activityparticipant__activityparticipantparameter__activityparticipantparameterval__value = 'accepted')&
                                           Q(activityresourceparameter__tpclass='status')&
                                           Q(activityresourceparameter__activityresourceparameterval__status = 'accepted')&
                                           Q(activityresourceparameter__activityresourceparameterval__value = 'accepted')&
                                           Q(participantresource__participant__participant = part)).distinct()
    if ares.count() == 0:
        return None
    amount = 0
    for ar in ares.all():
        a = ar.participantresource_set.filter(participant__participant = part).aggregate(Sum('amount'))
        if a != None and a['amount__sum'] != None:
            amount += float(a['amount__sum'])
    fullamount = get_full_resource_amount(res)
    fullavailable = get_full_resource_available(res)
    try:
        available = amount * fullavailable / fullamount
    except ZeroDivisionError:
        available = 0
    try:
        cost = get_full_resource_cost(res) * available / fullavailable
    except ZeroDivisionError:
        cost = 0
    ret = {'uuid' : res.uuid,
           'product' : res.product,
           'amount' : amount,
           'available' : available,
           'cost' : cost,
           'min_cost' : float(res.min_cost) * amount if res.min_cost != None else None,
           'max_cost' : float(res.max_cost) * amount if res.max_cost != None else None,
           'mean_cost' : float(res.mean_cost) * amount if res.mean_cost != None else None,
           'name' : res.name,
           'descr' : res.descr,
           'units' : res.measure.name,
           'use' : res.usage,
           'site' : res.site}
    return ret






def execute_contractor_offer_resource(params):
    try:
        res = Resource.objects.filter(uuid=params['uuid']).all()[0]
    except IndexError:
        return {'code' : RESOURCE_NOT_FOUND,
                'caption' : 'Resource is not found'}, httplib.PRECONDITION_FAILED

    try:
        cnt = Contractor.objects.filter(user_id = params['user']).all()[0]
    except IndexError:
        return {'code' : CONTRACTOR_NOT_FOUND,
                'caption' : 'Contractor is not found'}, httplib.PRECONDITION_FAILED
    am = params.get('amount')
    if am == None or am > 0.001:
        get_or_create_object(ContractorOffer, {'contractor' : cnt,
                                               'resource' : res},
                             {'amount' : params.get('amount'),
                              'cost' : params.get('cost')})
    else:
        ContractorOffer.objects.filter(Q(contractor=cnt) & Q(resource=res)).delete()
    return 'Created', httplib.CREATED


def execute_contractor_list_project_resources(params):
    try:
        prj = Project.objects.filter(uuid = params['uuid']).all()[0]
    except IndexError:
        return {'code' : PROJECT_NOT_FOUND,
                'caption' : 'Project is not found'}, httplib.PRECONDITION_FAILED
    ret = []
    for res in prj.resource_set.all():
        p = {'uuid' : res.uuid,
             'product' : res.product,
             'name' : res.name,
             'descr' : res.descr,
             'units' : res.measure.name,
             'use' : res.usage,
             'site' : res.site}
        amount = get_full_resource_amount(res)
        if amount <= 0.001:
            continue
        p['amount'] = amount
        us = get_full_resource_available(res)
        p['free_amount'] = p['amount'] - us
        ret.append(p)
    return ret, httplib.OK

def get_full_resource_available(res):
    ret = 0
    for a in res.contractorusage_set.all():
        x = get_object_parameter(a, tpclass = 'amount')
        if x != None:
            ret += float(x)
    return ret

def execute_list_contractors(params):
    ret = []
    for cnt in Contractor.objects.all():
        p = {'user' : cnt.user_id,
             'name' : cnt.name}
        pp = []
        for cntct in cnt.contractorcontact_set.all():
            pp.append({'type' : cntct.tp,
                       'value' : cntct.value})
        p['contacts'] = pp
        ret.append(p)
    return ret, httplib.OK

@get_user
def execute_set_resource_costs(params, user): #  FIXME: dirty
    try:
        resource = Resource.objects.filter(uuid = params['uuid']).all()[0]
    except IndexError:
        return {'code' : RESOURCE_NOT_FOUND,
                'caption' : 'Resource not found'}, httplib.PRECONDITION_FAILED
    prj = user.project
    if prj.ruleset != 'despot':
        return 'Project status is not "despot"', httplib.NOT_IMPLEMENTED
    if not user.is_initiator:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : 'you are not initiator'}, httplib.PRECONDITION_FAILED
    if params.get('min') != None:
        resource.min_cost = params['min']
    if params.get('max') != None:
        resource.max_cost = params['max']
    if params.get('cost') != None:
        resource.mean_cost = params['cost']
    resource.save(force_update=True)
    return 'changed', httplib.CREATED

def execute_check_user_exists(params):
    email = params['email']
    if User.objects.filter(email=email).count() == 1:
        return '', 200
    else:
        return '', 404

def execute_create_user_account(params):
    try:
        user = create_user(params['email'],
                           params['password'],
                           params['name'],
                           params.get('descr'))
    except IntegrityError:
        return '', 409
    return {'email' : user.email,
            'name' : user.name,
            'descr' : user.descr}, 201

def execute_ask_user_confirmation(params):
    email = params['email']
    try:
        user = User.objects.filter(email=email).all()[0]
    except IndexError:
        return {'code' : USER_NOT_FOUND,
                'caption' : 'This user is not exists'}, httplib.PRECONDITION_FAILED
    if user.is_active:
        return 'User is already activated', 409
    user.confirmation = hex4()
    user.save(force_update=True)
    try:
        site = Site.objects.get_current()
        send_mail(u'Подтверждение регистрации на сайте {0}'.format(site.name),
                  """Ваш код подтверждения
{0}
используйте его для подтверждения аккаунта или просто перйдите по ссылке
{1}""".format(user.confirmation,
              generate_user_magic_link('confirmation', user.confirmation)),
                  settings.EMAIL_HOST_USER,
                  [user.email])
    except Exception as e:
        print(str(e))
        return {'code' : EMAIL_CAN_NOT_BE_SENT,
                'caption' : 'Could not send the email'}, httplib.PRECONDITION_FAILED
    return return_if_debug({'confirmation' : user.confirmation}), httplib.OK

def execute_confirm_account(params):
    user = get_database_user(params['email'],
                             params['password'])
    if user == None or user.confirmation != params['confirmation']:
        return {'code' : USER_CONFIRMATION_FAILED,
                'caption' : 'Confirmation failed'}, httplib.PRECONDITION_FAILED
    user.is_active = True
    user.confirmation = None
    user.save(force_update=True)
    return '', 202

def execute_authenticate_user(params):
    user = auth_user(params['email'],
                     params['password'])
    if user == None:
        return {'code' : AUTHENTICATION_FAILED,
                'caption' : 'Authentication failed'}, httplib.PRECONDITION_FAILED
    return {'email' : user.email,
            'name' : user.name,
            'descr' : user.descr,
            'token' : user.token}, httplib.OK

def execute_confirm_user_by_long_confirmation(confirmation):
    """
    Arguments:

    - `confirmaion`:
    """
    try:
        u = User.objects.filter(confirmation=confirmation).all()[0]
    except IndexError:
        return '', 409
    else:
        u.is_active = True
        u.save(force_update=True)
        return '', 200

def execute_check_token(params):
    token = params['token']
    try:
        user = User.objects.filter(token=token).all()[0]
    except IndexError:
        try:
            partic = User.objects.filter(token=token).all()[0]
        except IndexError:
            return 'No such token', 409
        else:
            return {'temp' : True}, 200
    else:
        return {'temp' : False}, 200





def execute_logout(params):
    token = params['token']
    try:
        user = User.objects.filter(token=token).all()[0]
    except IndexError:
        try:
            partic = Participant.objects.filter(token=token).all()[0]
        except IndexError:
            return 'user not found', 409
        else:
            proj = partic.project
            if can_change_project(proj):
                partic.delete()
                kill_project_if_need(proj)
                return 'Participant deleted', 201
            else:
                return 'Project can not be changed', 201
    else:
        user.token = None
        user.save(force_update=True)
        return 'User token deleted', 201

def execute_check_project_participation(params):
    token = params['token']
    uuid = params['uuid']
    try:
        prj = Project.objects.filter(uuid = uuid).all()[0]
    except IndexError:
        return 'There is no such project', 409
        
    try:
        prt = Participant.objects.filter(token = token).all()[0]
    except IndexError:
        try:
            u = User.objects.filter(token = token).all()[0]
        except IndexError:
            return 'There is no such user', 409
        else:
            try:
                prt = Participant.objects.filter(Q(project = prj) & Q(user = u)).all()[0]
            except IndexError:
                return 'Do not participate', 409
            else:
                return {'initiator' : prt.is_initiator}, 200
    else:
        if prt.project == prj:
            return {'initiator' : prt.is_initiator}, 200
        else:
            return 'Do not particiapate', 409
                
def execute_exit_project(params):
    token = params['token']
    uuid = params['uuid']
    try:
        proj = Project.objects.filter(uuid=uuid).all()[0]
    except IndexError:
        return {'code' : PROJECT_NOT_FOUND,
                'caption' : 'Can not find project'}, 409
    else:
        try:
            user = User.objects.filter(token = token).all()[0]
        except IndexError:
            try:
                partic = Participant.objects.filter(token = token).all()[0]
            except IndexError:
                return {'code' : PARTICIPANT_NOT_FOUND,
                        'caption' : 'Can not find such participant'}, 409
            else:
                if can_change_project(proj):
                    partic.delete()
                    kill_project_if_need(proj)
                    return 'Participant deleted', httplib.CREATED
                else:
                    return {'code' : ACCESS_DENIED,
                            'caption' : 'Can not change project'}, httplib.PRECONDITION_FAILED
        else:
            if can_change_project(proj):
                Participant.objects.filter(Q(user=user) & Q(project=proj)).delete()
                kill_project_if_need(proj)
                return 'User exited', httplib.CREATED
            else:
                return {'code' : ACCESS_DENIED,
                        'caption' : 'Can not change project'}, httplib.PRECONDITION_FAILED
            
def kill_project_if_need(proj):
    if proj.participant_set.count() == 0:
        proj.delete()

def can_change_project(proj):
    st = get_object_status(proj)
    return st != 'closed'
