#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import check_safe_string, check_safe_string_or_null, \
    check_datetime_or_null, check_bool, check_string, check_string_choise, \
    check_string_or_null, string2datetime, check_int_or_null, check_string_choise_or_null, \
    datetime2dict, check_list_or_null
from services.models import Project, Participant, hex4, ParticipantVote, \
    ProjectParameter, ProjectParameterVl, ProjectParameterVal, DefaultParameter, \
    DefaultParameterVl, ProjectRulesetDefaults, ProjectParameterVote
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
    p = Project(name = parameters['name'], sharing=parameters['sharing'],
                ruleset=parameters['ruleset'])
    if 'descr' in parameters:
        p.descr = parameters['descr']
    if 'begin_date' in parameters:
        p.begin_date = string2datetime(parameters['begin_date'])
    else:
        p.begin_date=datetime.now()
    p.status = 'open'
    p.save()
    
    # создаем участника - владельца
    pr = Participant(project=p, name=parameters['user_name'])
    pr.psid=hex4()
    pr.token=hex4()
    pr.is_initiator=True
    if 'user_id' in parameters:
        pr.user = parameters['user_id']
    if 'user_descr' in parameters:
        pr.descr = parameters['user_descr']
    pr.status = u'accepted'
    pr.save()
    
    # создаем предложение на добавление участника
    pv = ParticipantVote(participant=pr, voter=pr, vote='include')
    pv.save()

    # заполняем дефолтные параметры проекта
    for prd in ProjectRulesetDefaults.objects.filter(Q(ruleset=p.ruleset) | Q(ruleset=None)).all():
        dpr = prd.parameter
        projpar = ProjectParameter(project=p, default_parameter=dpr,
                                   name=dpr.name, descr=dpr.descr,
                                   tp=dpr.tp, enum=dpr.enum)
        projpar.save()
        if dpr.enum:
            for enums in DefaultParameterVl.objects.filter(parameter=dpr).all():
                penum = ProjectParameterVl(parameter=projpar, value=enums.value, caption=enums.caption)
                penum.save()
                
        pval=ProjectParameterVal(parameter=projpar,
                                 value=dpr.default_value,
                                 dt=datetime.now(),
                                 status='accepted')
        if dpr.enum and DefaultParameterVl.objects.filter(Q(parameter=dpr) & Q(value=dpr.default_value)).count() == 0:
            print('Error in default parameters of project, default value not in posible values "{0}"'.format(dpr.uuid))
            return {'code' : PROJECT_PARAMETER_ERROR,
                    'caption' : 'Error in default parameters of project, default value not in posible values "{0}"'.format(dpr.uuid)}, httplib.INTERNAL_SERVER_ERROR
        pval.save()
    
    return {'project_uuid' : p.uuid,
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
        
    qry = None                  # сформированное условие для отбора
    if props.get('status') != None:
        qry = none_and(qry, Q(status=props['status']))
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
            return []           # количество проектов меньше чем начало куска который был запрошел
        ret = qr[ppp*pn:ppp*(pn+1)]
    else:                       # количество проектов на страницу не указано
        ret = qr

    return {'pages' : int(ceil(count / props.get('projects_per_page'))) if props.get('projects_per_page') != None else count,
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
    # проверяем есть ли пользователь с указанным user_id
    cnt = Participant.objects.filter(Q(user=user_id) | Q(token=user_id)).count()
    if cnt==0:
        return u'There is no one user found', httplib.NOT_FOUND
    # берем список участников с указанным user_id
    parts = Participant.objects.filter(Q(user=user_id) | Q(token=user_id)).all() # список участиков
    ret = []
    # формируем список проектов для соответствующего списка участников
    for part in parts:
        pr = Project.objects.get(participant=part) # связанный проект
        ret.append({'uuid' : pr.uuid,
                    'name' : pr.name,
                    'descr' : pr.descr,
                    'begin_date' : datetime2dict(pr.begin_date),
                    'initiator' : part.is_initiator,
                    'status' : pr.status})
    return ret, httplib.OK

def execute_change_project_status(params):
    """
    - `params`:
    """
    # проверяем наличие пользователя с указанным psid
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no participants with that psid', httplib.NOT_FOUND
    part = Participant.objects.filter(psid=params['psid']).all()
    # если участник не инициатор - выходим
    if part[0].is_initiator == False:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : u'this user is not initiator'}, httplib.PRECONDITION_FAILED
    prj = Project.objects.get(participant=part[0])
    # если проект не управляемый - выходим
    if prj.ruleset != 'despot':
        return {'code' : WRONG_PROJECT_RULESET,
                'caption' : u'project ruleset is not "despot"'}, httplib.PRECONDITION_FAILED
    # меняем статус проекта
    prj.status = params['status']
    prj.save()
    return '', httplib.CREATED

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

def execute_create_project_parameter_from_default(params):
    """
    Arguments:
    - `params`:
    """
    # проверяем наличие пользователя
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no such user', httplib.NOT_FOUND
    # проверяем наличие дефолт параметра пректа
    dpr = DefaultParameter.objects.get(uuid=params['uuid'])
    if dpr == None:
        return {'code' : DEFAULT_PARAMETER_NOT_FOUND,
                'caption' : u'There is no such default parameter'}, httplib.PRECONDITION_FAILED
    # достаем данные из дефолт параметра и передаем их execute_create_project_parameter
    r = {'psid' : params['psid'],
         'name' : dpr.name,
         'descr' : dpr.descr,
         'tp' : dpr.tp,
         'enum' : dpr.enum,
         'value' : dpr.default_value}
    # значение перечисляемое - добавляем перечисляемые значения
    if dpr.enum:
        rvs = []
        for x in DefaultParameterVl.objects.filter(parameter=dpr).all():
            rvs.append({'value' : x.value,
                        'caption' : x.caption})
        r['values'] = rvs
    return execute_create_project_parameter(r)

def execute_create_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    # проверяем наличие пользователя с указанным psid
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no participants with that psid', httplib.NOT_FOUND
    # выбираем проект для соответствующего пользователя
    proj = Project.objects.filter(participant__psid=params['psid']).all()[0]
    # проверяем тип проекта и вызываем соответствующий обработчик
    if proj.ruleset == 'despot':
        return despot_create_project_parameter(proj, params)
    else:
        return u'Create project parameter is not implemented for ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED
    
def despot_create_project_parameter(proj, params):
    """
    create parameter for despot ruleset project
    Arguments:
    - `params`:
    """
    # проверяем является ли пользователь инициатором
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if user.is_initiator == False:
        return {'code' : MUST_BE_INITIATOR,
                'caption' : u'You must be initiator if project is "despot" ruleset'}, httplib.PRECONDITION_FAILED
    # формируем параметр
    projpar = ProjectParameter(project=proj, name=params['name'],
                               tp=params['tp'], enum=params['enum'])
    if params.get('descr') != None:
        projpar.descr = params['descr']
    # пытаемся сохранить параметр
    try:
        projpar.save()        # сохранили параметр проекта
    except IntegrityError:
        return {'code' : PROJECT_PARAMETER_ALREADY_EXISTS,
                'caption' : u'The project has a parameter with the same name'}, httplib.PRECONDITION_FAILED
    # если параметр с ограниченным набором значений заполняем набор
    if params['enum']:
        for v in params['values']:
            vs = ProjectParameterVl(parameter=projpar,
                                    value=v['value'])
            if v.get('caption') != None:
                vs.caption=v['caption']
            # пробуем сохранить, если значения одинаковые - пропускаем вставку
            try:
                vs.save()
            except IntegrityError:
                pass
    # вызываем изменение значения параметра
    return despot_change_project_parameter(proj, {'psid' : params['psid'],
                                                  'uuid' : projpar.uuid,
                                                  'value' : params['value'],
                                                  'caption' : params.get('caption')})

def execute_change_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    # проверяем есть ли пользователь с указанным psid
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no user with this psid', httplib.NOT_FOUND
    # проверяем отностися ли параметр к проекту указанного пользователя
    proj = Project.objects.filter(participant__psid=params['psid']).all()[0]
    par = ProjectParameter.objects.get(uuid=params['uuid'])
    if par == None:
        return {'code' : PROJECT_PARAMETER_NOT_FOUND,
                'caption' : u'There is no such parameter'}, httplib.PRECONDITION_FAILED
    if par.project != proj:
        return {'code' : ACCESS_DENIED,
                'caption' : u'This user can not change specified parameter'}, httplib.PRECONDITION_FAILED
    # выбираем обработчик для соответствующего типа проекта
    if proj.ruleset == 'despot':
        return despot_change_project_parameter(proj, params)
    else:
        return u'Change parameter is not implemented for project with ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED

def despot_change_project_parameter(proj, params):
    """
    Arguments:
    - `proj`:
    - `params`:
    """
    par = ProjectParameter.objects.get(uuid=params['uuid'])
    # если параметр перечисляемый, проверяем входил ли значение в список возможных значений
    if par.enum:
        if ProjectParameterVl.objects.filter(Q(parameter=par) & Q(value=params['value'])).count() == 0:
            return {'code' : PROJECT_PARAMETER_ERROR,
                    'caption' : u'This value can not set for enumerated parameter'}, httplib.PRECONDITION_FAILED
    # если мы еще не предлагали это значение параметра, то создаем предложение. Иначе меняем старое
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter=par) & Q(projectparametervote__voter=user) & Q(projectparametervote__vote=u'change')).count() == 0: #нет значений предложынных нами
        np = ProjectParameterVal(parameter=par, status='voted', dt=datetime.now(),
                                 value=params['value'])
        if params.get('caption') != None:
            np.caption = params['caption']
        np.save()
        npvote = ProjectParameterVote(parameter_val=np, voter=user, vote='change')
        npvote.save()
    else:                                 # изменяем значение которое мы уже предложили
        np = ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter=par) & Q(projectparametervote__voter=user) & Q(projectparametervote__vote=u'change')).all()[0]
        np.value = params['value']
        if params.get('caption') != None:
            np.caption = params['caption']
        np.save()
    # согласуем предложенный параметр
    return execute_conform_project_parameter({'psid' : params['psid'],
                                              'uuid' : par.uuid})

def execute_conform_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    # проверяем наличие пользователя с указанным psid
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no users with specified psid', httplib.NOT_FOUND
    # проверяем есть ли такой параметр и находиться ли он в том же проекте что и пользователь
    pr = ProjectParameter.objects.get(uuid=params['uuid'])
    if pr == None:
        return {'code' : PROJECT_PARAMETER_NOT_FOUND,
                'caption' : u'There is no such parameters'}, httplib.PRECONDITION_FAILED
    proj = Project.objects.filter(participant__psid=params['psid']).all()[0]
    if pr.project != proj:
        return {'code' : ACCESS_DENIED,
                'caption' : u'Parameter is not assigned to specified project'}, httplib.PRECONDITION_FAILED
    # вызываем обработчик для соответствующего типа проекта
    if proj.ruleset == 'despot':
        return despot_conform_project_parameter(proj, params)
    else:
        return u'conform parameter is not implemented for ruleset "{0}"'.format(proj.ruleset), httplib.NOT_IMPLEMENTED


def despot_conform_project_parameter(proj, params):
    """
    conform project with 'despot' ruleset
    Arguments:
    - `proj`:
    - `params`:
    """
    # если пользователь - инициатор: присваиваем предложенное пользователем значение как текущее значение параметра
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if user.is_initiator:
        # проверяем есть ли предложенные значения
        if ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter__uuid=params['uuid']) & Q(projectparametervote__voter=user)).count() == 0:
            return u'There is nothing to conform (no votes)', httplib.CREATED
        # если есть присваиваем ему статус accepted, остальным присваиваем denied
        vl = ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter__uuid=params['uuid']) & Q(projectparametervote__voter=user)).all()[0]
        ProjectParameterVal.objects.filter(Q(status='accepted') & Q(parameter__uuid=params['uuid'])).update(status='changed')
        vl.status='accepted'
        vl.save()
        ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter__uuid=params['uuid'])).update(status='denied')
        return u'Accepted new value', httplib.CREATED
    else:                                 #пользователь не инициатор - согласование ничего неделает
        return u'User is not initiator, conform doing nothing', httplib.CREATED
    
def execute_list_project_parameters(psid):
    """
    Arguments:
    - `psid`: psid as string
    """
    # проверяем есть ли пользователь 
    if Participant.objects.filter(psid=psid).count() == 0:
        return u'There is no user with such psid', httplib.NOT_FOUND
    proj = Project.objects.filter(participant__psid=psid).all()[0]
    ret = []
    for param in ProjectParameter.objects.filter(project=proj).all():
        p = {'uuid' : param.uuid,
             'name' : param.name,
             'descr' : param.descr,
             'tp' : param.tp,
             'enum' : param.enum}
        if param.default_parameter == None:
            p['tecnical'] = False
        else:
            p['tecnical'] = param.default_parameter.tecnical
        if param.enum:          # параметр перечисляемый - добавляем возможные значения
            vs = []
            for v in ProjectParameterVl.objects.filter(parameter=param).all():
                vs.append({'value': v.value,
                           'caption' : v.caption})
            p['values'] = vs
        if ProjectParameterVal.objects.filter(Q(parameter=param) & Q(status='accepted')).count() > 0: # есть принятое значение параметра
            pv = ProjectParameterVal.objects.filter(Q(parameter=param) & Q(status='accepted')).all()[0]
            p['value'] = pv.value
            p['caption'] = pv.caption
        votes = []
        for vts in ProjectParameterVal.objects.filter(Q(parameter=param) & Q(status='voted')).all(): # проходим по предложенным значениям
            x = vts.projectparametervote_set.all()[0] # объект предложения
            v = {'uuid', x.voter.uuid,
                 'value', vts.value,
                 'caption', vts.caption,
                 'dt', vts.dt}
            votes.append(v)

        
        ret.append(p)
    return ret, httplib.OK

def execute_change_participant(params):
    """
    
    Arguments:
    - `params`:
    """
    # проверяем наличие пользователя по psid
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is no such user', httplib.NOT_FOUND
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if Participant.objects.filter(uuid=params['uuid']).count() == 0:
        return {'code' : PARTICIPANT_NOT_FOUND,
                'caption' : 'There is no participants found'}, httplib.PRECONDITION_FAILED
    par = Participant.objects.filter(uuid=params['uuid']).all()[0]
    def check_user(par, user):
        # проверка того, что пользователь меняет себя или приглашенного, который еще не входил
        if par.uuid == user.uuid:
            return True
        if par.project != user.project:
            return False
        if user.dt == None and ParticipantVote.objects.filter(Q(voter=par) & Q(participant=user) & Q(vote=u'include')).count() > 0:
            return True
        return False

    if not check_user(par, user):
        return {'code' : ACCESS_DENIED,
                'caption' : u'You can not change this user'}, httplib.PRECONDITION_FAILED
    # изменяем параметр пользователя
    if params.get('name') != None:
        user.name = params['name']
    if params.get('descr') != None:
        user.descr = params['descr']
    if params.get('user_id') != None:
        user.user = params['user_id']
    user.save()
    return 'OK', httplib.CREATED

def execute_list_participants(psid):
    if Participant.objects.filter(psid=psid).count() == 0:
        return u'There is no such psid', httplib.NOT_FOUND
    prj = Project.objects.filter(participant__psid=psid).all()[0]
    ret = []
    # получаем список участников проекта
    for par in Participant.objects.filter(project=prj):
        a = {'uuid' : par.uuid,
             'descr' : par.descr,
             'status' : par.status}
        # смотрим список предложений по участнику
        if par.status == 'voted':
            vts = []
            for vote in ParticipantVote.objects.filter(Q(participant=par) & Q(voter__project=prj)).all():
                vts.append({'voter' : vote.voter,
                            'vote' : vote.vote,
                            'comment' : vote.comment,
                            'dt' : vote.create_date})
            a['votes'] = vts
        ret.append(a)
    return ret, httplib.OK
    
def execute_invite_participant(params):
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return u'There is user with such psid', httplib.NOT_FOUND
    # создаем нового участника для приглашения
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    pr = Participant(project=user.project, name=params['name'],
                     token=hex4(), status='voted')
    if params.get('descr') != None:
        pr.descr = params['descr']
    if params.get('user_id') != None:
        pr.user = params['user_id']
    try:
        pr.save()
    except IntegrityError:
        return u'User with such name or with such user_id is already exists in this project', httplib.PRECONDITION_FAILED
    # создаем приглашение участника
    vt = ParticipantVote(participant=pr, voter=user, vote='include')
    if params.get('comment') != None:
        vt.comment = params['comment']
    vt.save()
    # согласуем предложение
    r, st = execute_conform_participant({'psid' : params['psid'],
                                         'uuid' : pr.uuid})
    if st == httplib.CREATED:
        return pr.token, httplib.CREATED
    else:
        return r, st

def execute_conform_participant(params):
    pass

def execute_enter_project_open(params):
    if Project.objects.filter(uuid=params['uuid']).count() == 0:
        return {'code' : PROJECT_NOT_FOUND,
                'caption' : 'No such project'}, httplib.PRECONDITION_FAILED
    prj = Project.object.filter(uuid=params['uuid']).all()[0]
    
    if prj.ruleset != 'open':
        return {'code' : PROJECT_MUST_BE_OPEN,
                'caption' : 'You can join just to open projects'}, httplib.PRECONDITION_FAILED
    if prj.status != 'planning':
        return {'code' : PROJECT_STATUS_MUST_BE_PLANNING,
                'caption' : 'Project status is not "planning"'}, httplib.PRECONDITION_FAILED
    prt = Participant(project=prj, dt=datetime.datetime.now(),
                      is_initiator=False, psid=hex4(), token=hex4(), name=params['name'],
                      status='accepted')
    if params.get('descr') != None:
        prt.descr = params['descr']
    if params.get('user_id') != None:
        prt.user = params['user_id']
    try:
        prt.save()
    except IntegrityError:
        return {'code' : PARTICIPANT_ALREADY_EXISTS,
                'caption' : 'There is one participant with such name or user_id in this project'}
    pvt = ParticipantVote(voter=prt, participant=prt, vote='include',
                          comment=u'Участник самостоятельно подключился к проекту')
    pvt.save()
    return {'psid' : prt.psid,
            'token' : prt.token}, httplib.CREATED

def execute_enter_project_invitation(params):
    if Project.objects.filter(uuid=params['uuid']).count() == 0:
        return {'code' : PROJECT_NOT_FOUND,
                'caption' : 'There is no such project'}, httplib.PRECONDITION_FAILED
    prj = Project.objects.filter(uuid=params['uuid']).all()[0]
    if Participant.objects.filter(Q(project=prj) & (Q(token=params['token']) | Q(user=params['token']))).count() == 0:
        return {'code' : PARTICIPANT_NOT_FOUND,
                'caption' : 'There is no participants with such token or user_id'}, httplib.PRECONDITION_FAILED
    prt = Participant.objects.filter(Q(project=prj) & (Q(token=params['token']) | Q(user=params['token']))).all()[0]
    prt.dt = datetime.datetime.now()
    prt.psid = hex4()
    prt.save()
    return {'psid' : prt.psid}, httplib.CREATED
