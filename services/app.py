#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import get_or_create_object, get_user, get_authorized_user, \
    get_object_by_uuid, get_activity_from_uuid, get_activity_parameter_from_uuid, string2datetime, create_object_parameter, \
    set_object_status, set_object_parameter, get_object_status, get_object_parameter, create_object_parameter_from_default, \
    set_vote_for_object_parameter, get_vote_value_for_object_parameter, set_as_accepted_value_of_object_parameter, \
    get_or_create_object_parameter, get_resource_from_uuid, get_activity_resource_from_parameter, check_activity_resource_status, \
    get_authorized_activity_participant
from services.models import Project, Participant, hex4, ProjectParameter, ProjectParameterVl, ProjectParameterVal, \
    DefaultParameter,  DefaultParameterVl, ProjectRulesetDefaults, ProjectParameterVote, ActivityParticipant, \
    Activity, ActivityParameter, ActivityParameterVal, ActivityParameterVl, ActivityParameterVote, ParticipantParameterVal, \
    Resource, MeasureUnits, ActivityResourceParameterVote, ParticipantResource, ActivityResource
from services.statuses import *
from django.db import transaction, IntegrityError
from django.db.models import Q
from datetime import datetime
from math import ceil
import httplib


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
        pr.user = parameters['user_id']
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

    qry = Q(sharing='open')     # сформированное условие для отбора
    if props.get('status') != None:
        qry = none_and(qry, (Q(projectparameter__tpclass='status') & Q(projectparameter__projectparameterval__status='accepted') & Q(projectparameter__projectparameterval__value=props['status'])))
    if props.get('begin_date') != None:
        qry = none_and(qry, Q(begin_date__gte = string2datetime(props['begin_date'])))
    if props.get('search') != None:
        qry = none_and(qry, (Q(name__contains=props['search']) | Q(descr__contains=props['search'])))

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
            return {'pages' : int(ceil(float(count) / ppp)),
                    'projects' : []} # количество проектов меньше чем начало куска который был запрошел
        ret = qr[ppp*pn:ppp*(pn+1)]
    else:                       # количество проектов на страницу не указано
        ret = qr

    return {'pages' : int(ceil(float(count) / props.get('projects_per_page'))) if props.get('projects_per_page') != None else count,
            'projects' : [{'uuid' : a.uuid,
                           'name' : a.name,
                           'descr' : a.descr,
                           'begin_date' : a.begin_date.isoformat()} for a in ret]}

def execute_list_user_projects(user_id):
    """return tuple of response and status
    response is json encodable answer, list of projects assigned to given user_id
    
    Arguments:
    
    - `user_id`:
    
    Return:
    
    (`response`, `answer`)
    """
    # берем список участников с указанным user_id
    parts = Participant.objects.filter(Q(user=user_id) | Q(token=user_id)).all() # список участиков
    ret = []
    # формируем список проектов для соответствующего списка участников
    for part in parts:
        pr = part.project # связанный проект
        ret.append({'uuid' : pr.uuid,
                    'name' : pr.name,
                    'descr' : pr.descr,
                    'begin_date' : pr.begin_date.isoformat() if pr.begin_date != None else None,
                    'initiator' : part.is_initiator,
                    'status' : get_object_status(pr)})
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
        if par.dt == None:
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
        par.user = params['user_id']
    try:
        par.save()
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'Participant with such name already exists'}, httplib.PRECONDITION_FAILED

    return 'OK', httplib.CREATED

@get_user
def execute_list_participants(params, part):
    prj = part.project
    ret = []
    # получаем список участников проекта
    for par in Participant.objects.filter(project=prj).all():
        a = {'uuid' : par.uuid,
             'name' : par.name,
             'descr' : par.descr,
             'me' : part.uuid == par.uuid,
             'status' : get_object_status(par)}

        # смотрим список предложений по участнику
        vts = []
        for ps in ParticipantParameterVal.objects.filter(Q(parameter__tpclass='status') & Q(parameter__obj=par) & Q(status='voted')).all(): #все предложенные статусы участника
            for pvt in ps.participantparametervote_set.all():   #все предложения по каждому статусу
                vts.append({'voter' : pvt.voter.uuid,
                            'vote' : 'include' if ps.value == 'accepted' else 'exclude',
                            'comment' : pvt.comment})
        a['votes'] = vts
        ret.append(a)

    return ret, httplib.OK

@get_user
def execute_invite_participant(params, user):
    prj = user.project
    if prj.sharing == 'close':  # проект закрытый
        if prj.ruleset == 'despot' and (not user.is_initiator):
            return {'code' : MUST_BE_INITIATOR,
                    'caption' : 'You must be initiator to invite users to the close project'}, httplib.PRECONDITION_FAILED
    else:                       # проект открытый или по приглашению
        if  get_object_status(prj) != 'planning':
            return {'code' : PROJECT_STATUS_MUST_BE_PLANNING,
                    'caption' : 'Project is not in the planning status'}, httplib.PRECONDITION_FAILED

    # создаем нового или берем существующего участника
    q = {'name' : params['name'],
         'project' : prj}
    if params.get('user_id') != None:
        q['user'] = params['user_id']

    try:
        def check(p):
            return prj.ruleset == 'despot' and user.is_initiator

        part = get_or_create_object(Participant, q, {'descr' : params.get('descr'),
                                                     'user' : params.get('user_id')},
                                    can_change = check)
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'This participant already exists, try repeat this query but do not specify "user_id" field or specify the same value'}, httplib.PRECONDITION_FAILED
    if part == None:            # в том случае если пользователь есть но мы не можем менять атрибуты
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'This participant already exists, try repeat this query but do not specify "user_id" and "descr" fields or specify the same value'}, httplib.PRECONDITION_FAILED

    pstat = get_object_status(part)
    if get_object_status(part) == 'denied': # пользователь уже был и он запрещен
        return {'code' : PARTICIPANT_DENIED,
                'caption' : 'This participant has denied status, so you can not invite him/her again'}, httplib.PRECONDITION_FAILED

    if part.token == None:      # создаем токен если нету
        part.token = hex4()
        part.save()

    prmt = get_or_create_object_parameter(part, 'status', True, values = [{'value' : a[0], 'caption' : a[1]} for a in Participant.PARTICIPANT_STATUS])
    set_object_parameter(part, user, 'voted', uuid = prmt.uuid)
    set_vote_for_object_parameter(part, user, 'accepted', uuid = prmt.uuid, comment = params.get('comment'))

    return {'token' : part.token}, httplib.CREATED

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
    if prj.sharing != 'open':
        return {'code' : PROJECT_MUST_BE_OPEN,
                'caption' : 'You can join just to open projects'}, httplib.PRECONDITION_FAILED
    if get_object_status(prj) != 'planning':
        return {'code' : PROJECT_STATUS_MUST_BE_PLANNING,
                'caption' : 'Project status is not "planning"'}, httplib.PRECONDITION_FAILED
    prt = Participant(project=prj, dt=datetime.now(),
                      is_initiator=False, psid=hex4(), token=hex4(), name=params['name'])

    if params.get('descr') != None:
        prt.descr = params['descr']
    if params.get('user_id') != None:
        prt.user = params['user_id']
    try:
        prt.save()
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
        prt = Participant.objects.filter(Q(project=prj) & (Q(token=params['token']) | Q(user=params['token']))).all()[0]
    except IndexError:
        return {'code' : PARTICIPANT_NOT_FOUND,
                'caption' : 'There is no participants with such token or user_id'}, httplib.PRECONDITION_FAILED

    if get_object_status(prt) != 'accepted':
        return {'code' : ACCESS_DENIED,
                'caption' : 'You are not allowerd user (not accepted status) to do enter to the project'}, httplib.PRECONDITION_FAILED
    prt.dt = datetime.now()
    prt.psid = hex4()
    prt.save()
    return {'psid' : prt.psid}, httplib.CREATED

@get_user
def execute_exclude_participant(params, user):
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
@get_object_by_uuid(Participant, PARTICIPANT_NOT_FOUND,
                    u'Participant with such uuid has not been found')
def execute_conform_participant_vote(params, part, user):
    status = get_object_status(part)
    if params['vote'] == 'exclude':
        if status == 'denied':
            return 'Participant is already denied', httplib.CREATED
    elif status == 'accepted':
        return 'Participant is already accepted', httplib.CREATED

    set_vote_for_object_parameter(part, user, 'accepted', tpclass = 'status', comment = params.get('comment'))

    # согласуем участника
    return execute_conform_participant({'psid' : params['psid'],
                                        'uuid' : part.uuid})

@get_user
def execute_list_activities(params, user):
    prj = user.project
    ret = []
    for act in prj.activity_set.filter(Q(activityparameter__tpclass='status') &
                                       Q(activityparameter__activityparameterval__status='accepted') &
                                       (Q(activityparameter__activityparameterval__value__in=['voted', 'accepted', 'denied']) |
                                        (Q(activityparameter__activityparameterval__value='created') &
                                         Q(activityparameter__activityparameterval__activityparametervote__voter=user)))).distinct().all():

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
        a['participant'] = ActivityParticipant.objects.filter(Q(participant=user) &
                                                              Q(activity=act) &
                                                              Q(activityparticipantparameter__tpclass='status') &
                                                              Q(activityparticipantparameter__activityparticipantparameterval__status='accepted') &
                                                              Q(activityparticipantparameter__activityparticipantparameterval__value='accepted')).count() > 0

        ret.append(a)

    return ret, httplib.OK

@get_user
@get_activity_from_uuid()
def execute_activity_participation(params, act, user):
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
        return 'This activity is already public', httplib.CREATED
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
    set_as_accepted_value_of_object_parameter(astv)
    return 'Status changed', httplib.CREATED

@get_object_by_uuid(Activity, ACTIVITY_NOT_FOUND, 'There is no such activity')
def execute_activity_list_participants(params, act):
    if get_object_status(act) != 'accepted':
        return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                'caption' : 'Status of this is activity is not "accepted"'}, httplib.PRECONDITION_FAILED
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
    for prm in act.activityparameter_set.filter(Q(tpclass='user') &
                                                (Q(activityparameterval__status='accepted') |
                                                 Q(activityparameterval__status=None))).all():
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
       except IndexError:
           pass


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
    prj = user.project
    if prj.ruleset == 'despot' :
        return despot_conform_activity_parameter(params, ap, user)
    else:
        return 'Can not conform activity parameter in this project for now', httplib.NOT_IMPLEMENTED

def despot_conform_activity_parameter(params, ap, user):
    if not user.is_initiator:
        return 'You are not initiator, just ignore', httplib.CREATED
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
@check_activity_resource_status
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

@get_user
def execute_list_activity_resources(params, user):
    if isinstance(params.get('uuid'), basestring):
        return list_activity_resources(params, user)
    else:
        return list_project_resources(params, user)

@get_activity_from_uuid()
def list_activity_resources(params, act, user):
    ret = []
    for ar in act.activityresource_set.filter(Q(activityresourceparameter__tpclass = 'status') &
                                              Q(activityresourceparameter__activityresourceparameterval__status = 'accepted') &
                                              Q(activityresourceparameter__activityresourceparameterval__value__in = ['accepted', 'voted'])).all():
        res = ar.resource
        p = {'uuid' : res.uuid,
             'name' : res.name,
             'descr' : res.descr,
             'units' : res.measure.name,
             'status' : get_object_status(ar),
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
            apar = get_authorized_activity_participant(user, act)
            if isinstance(apar, ActivityParticipant):
                try:
                    pres = ar.participantresource_set.filter(participant=apar).distinct().all()[0]
                    p['used'] = True
                    p['amount'] = float(pres.amount)
                except IndexError:
                    pass
        ret.append(p)
    return ret, httplib.OK

def list_project_resources(params, user):
    prj = user.project
    ret = []
    for res in prj.resource_set.all():
        p = {'uuid' : res.uuid,
             'name' : res.name,
             'descr' : res.descr,
             'units' : res.measure.name,
             'status' : 'accepted',
             'use' : res.usage,
             'site' : res.site,
             'votes' : [],
             'used' : False,
             'amount' : 0}
        ret.append(p)
    return ret, httplib.OK


@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
def execute_include_activity_resource(params, res, act, user):
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
        return "Has already", httplib.CREATED
    elif st == 'denied':
        return {'code' : ACTIVITY_RESOURCE_NOT_ACCEPTED,
                'caption' : 'This resource is denied on this activity'}, httplib.PRECONDITION_FAILED
    set_vote_for_object_parameter(ap, user, 'accepted', tpclass = 'status',
                                  comment = params.get('comment'))
    return conform_activity_resource(params, ap, res, act, user)

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
def execute_exclude_activity_resource(params, res, act, user):
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
    if not user.is_initiator:
        return 'You are not initiator, ignore', httplib.CREATED

    st = get_object_status(actres)
    if st == 'denied':
        return {'code' : ACTIVITY_RESOURCE_NOT_ACCEPTED,
                'caption' : 'This resource is denied on the activity'}, httplib.PRECONDITION_FAILED

    vtval = get_vote_value_for_object_parameter(actres, user, tpclass = 'status')
    set_as_accepted_value_of_object_parameter(vtval)
    return "Created", httplib.CREATED

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
@check_activity_resource_status
def execute_create_resource_parameter(params, ares, res, act, user):
    try:
        prm = create_object_parameter(ares, 'user', False, tp = params['tp'],
                                      name = params['name'], descr = params.get('descr'),
                                      values = params.get('values') if params['enum'] else [])
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exist'}, httplib.PRECONDITION_FAILED

    if isinstance(params.get('value'), basestring):
        return change_resource_parameter(params, prm, ares, res, act, user)
    else:
        return 'Created', httplib.CREATED
    

@get_user
@get_activity_from_uuid('activity')
@get_resource_from_uuid()
@get_activity_resource_from_parameter
@check_activity_resource_status
def execute_create_resource_parameter_from_default(params, ares, res, act, user):
    try:
        default = DefaultParameter(uuid=params['default']).all()[0]
    except IndexError:
        return {'code' : DEFAULT_PARAMETER_NOT_FOUND,
                'caption' : 'There is no such default parameter'}, httplib.PRECONDITION_FAILED
    try:
        prm = create_object_parameter_from_default(ares, default)
    except IntegrityError:
        return {'code' : RESOURCE_PARAMETER_ALREADY_EXISTS,
                'caption' : 'This parameter is already exists'}, httplib.PRECONDITION_FAILED
    if default.default_value != None:
        return change_resource_parameter(params, prm, ares, res, act, user)
    else:
        return 'Created', httplib.CREATED


def execute_list_activity_resource_parameters(params):
    pass

def execute_change_resource_parameter(params):
    pass

def execute_conform_resource_parameter(params):
    pass
