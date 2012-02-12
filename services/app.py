#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import check_safe_string, check_safe_string_or_null, \
    check_datetime_or_null, check_bool, check_string, check_string_choise, \
    check_string_or_null, dict2datetime, check_int_or_null, check_string_choise_or_null, \
    datetime2dict, check_list_or_null
from services.models import Project, Participant, hex4, ParticipantVote, \
    ProjectParameter, ProjectParameterVl, ProjectParameterVal, DefaultParameter, \
    DefaultParameterVl, ProjectRulesetDefaults
from django.db import transaction
from django.db.models import Q
from datetime import datetime
import httplib

def execute_create_project(parameters):
    """create project and related objects based on parameters
    Arguments:
    - `parameters`: dict with parametes
    """
    p = Project(name = parameters['name'], sharing=parameter['sharing'],
                ruleset=parameter['ruleset'])
    if 'description' in parameters:
        p.description = parameters['description']
    if 'begin_date' in parameters:
        p.begin_date = dict2datetime(parameters['begin_date'])
    else:
        p.begin_date=datetime.now()
    p.status = 'opened'
    p.save()
    
    # создаем участника - владельца
    pr = Participant(project=p, name=parameters['user_name'])
    pr.psid=hex4()
    pr.token=hex4()
    pr.is_initiator=True
    if 'user_id' in parameters:
        pr.user = parameters['user_id']
    if 'user_description' in parameters:
        pr.descr = parameters['user_description']
    pr.status = u'accepted'
    pr.save()
    
    # создаем предложение на добавление участника
    pv = ParticipantVote(participant=pr, voter=pr, vote='include', status='accepted')
    pv.save()

    # заполняем дефолтные параметры проекта
    for dpr in DefaultParameter.objects.filter(Q(projectrulesetdefaults__ruleset=p.ruleset) | Q(projectrulesetdefaults__ruleset=None)).all():
        projpar = ProjectParameter(project=p, default_parameter=dpr,
                                   name=dpr.name, descr=dpr.descr,
                                   tp=dpr.tp, enum=dpr.enum)
        projpar.save()
        if dpr.enum:
            for enums in DefaultParameterVl.objects.filter(parameter=dpr).all():
                penum = ProjectParameterVl(parameter=projpar, value=enums.value, caption=enums.caption)
                penum.save()
        else:
            pval=ProjectParameterVal(parameter=projpar,
                                     value=dpr.default_value,
                                     dt=datetime.now(),
                                     status='accepted')
            pval.save()
    
    return {'project_uuid' : p.uuid,
            'psid' : pr.psid,
            'token' : pr.token}

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
        qry = none_and(qry, Q(begin_date__gte=dict2datetime(props['begin_date'])))
    if props.get('search') != None:
        qry = none_and(qry, (Q(name__contains=props['search']) | Q(descr__contains=props['search'])))

    qr = None                   # сформированный запрос для выборки
    if qry == None:
        qr = Project.objects.all()
    else:
        qr = Project.objects.filter(qry).all()

    ret = None                                 # запрос с ограниченным количеством проектов
    if props.get('projects_per_page') != None: # указано количество пректов на страницу
        pn = props.get('page_number') if int(props.get('page_number')) != None else 0 # номер страницы
        ppp = int(props['projects_per_page']) # количество проектов на страницу
        if qr.count() < pn*ppp:
            return []           # количество проектов меньше чем начало куска который был запрошел
        ret = qr[ppp*pn:ppp*(pn+1)]
    else:                       # количество проектов на страницу не указано
        ret = qr

    return [{'uuid' : a.uuid,
             'name' : a.name,
             'descr' : a.descr,
             'begin_date' : datetime2dict(a.begin_date)} for a in ret]

def execute_user_projects(user_id):
    """return tuple of response and status 
    response is json encodable answer, list of projects assigned to given user_id
    Arguments:
    - `user_id`:
    Return:
    (`response`, `answer`)
    """
    cnt = Participant.objects.filter(user=user_id).count()
    if cnt==0:
        return [u'There is no one user found'], httplib.NOT_FOUND
    parts = Participant.objects.filter(user=user_id).all() # список участиков
    ret = []
    for part in parts:
        pr = Project.objects.get(participant=part) # вязанный проект
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
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return [u'There is no participants with that psid'], httplib.NOT_FOUND
    part = Participant.objects.filter(psid=params['psid']).all()
    if part[0].is_initiator == False:
        return [u'this user is not initiator'], httplib.PRECONDITION_FAILED
    prj = Project.objects.get(participant=part[0])
    if prj.ruleset != 'despot':
        return [u'project ruleset is not "despot"'], httplib.PRECONDITION_FAILED
    prj.status = params['status']
    prj.save()
    return '', httplib.OK

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

def execute_create_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return [u'There is no participants with that psid'], httplib.NOT_FOUND
    proj = Project.objects.filter(participant__psid=params['psid']).all()[0]
    if proj.ruleset='despot':
        despot_create_project_parameter(proj, params)
    else:
        return [u'Create project parameter is not implemented for ruleset "{0}"'.format(proj.ruleset)], httplib.NOT_IMPLEMENTED
    
def despot_create_project_parameter(proj, params):
    """
    create parameter for despot ruleset project
    Arguments:
    - `params`:
    """
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if user.is_initiator == False:
        return [u'You must be initiator if project is "despot" ruleset'], httplib.PRECONDITION_FAILED
    projpar = ProjectParameter(project=proj, name=params['name'],
                               tp=params['tp'], enum=params['enum'])
    if params.get('descr') != None:
        projpar.descr = params['descr']
    projpar.save()        # сохранили параметр проекта
    if params['enum']:                    # параметр имеет ограниченный набор значений
        for v in params['values']:
            vs = ProjectParameterVl(parameter=projpar,
                                    value=v['value'])
            if isinstance(v['caption'], basestring):
                vs.caption=v['caption']
            vs.save()
    return execute_change_project_parameter({'psid' : params['psid'],
                                             'uuid' : projpar.uuid,
                                             'value' : params['value'],
                                             'caption' : params.get('caption')})
    

def execute_change_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    if Participant.objects.filter(psid=params['psid']).count() == 0:
        return [u'There is no user with this psid'], httplib.NOT_FOUND
    proj = Project.objects.filter(participant__psid=params['psid']).all()[0]
    if proj.ruleset == 'despot':
        despot_change_project_parameter(proj, params)
    else:
        return [u'Change parameter is not implemented for project with ruleset "{0}"'.format(proj.ruleset)], httplib.NOT_IMPLEMENTED

def despot_change_project_parameter(proj, params):
    """
    Arguments:
    - `proj`:
    - `params`:
    """
    user = Participant.objects.filter(psid=params['psid']).all()[0]
    if user.is_initiator == False:
        return [u'If project ruleset if "despot" then you must be initiator to change parameter'], httplib.PRECONDITION_FAILED
    par = ProjectParameter.objects.get(uuid=params['uuid'])
    if ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter=par) & Q(projectparametervote__voter=user)).count() == 0: #нет значений предложынных нами
        np = ProjectParameterVal(parameter=par, status='voted', dt=datetime.now(),
                                 value=params['value'])
        if isinstance(params.get('caption'), basestring):
            np.caption = params['caption']
        np.save()
        npvote = ProjectParameterVote(parameter_val=np, voter=user, vote='change')
        npvote.save()
    else:                                 # изменяем значение которое мы уже предложили
        np = ProjectParameterVal.objects.filter(Q(status='voted') & Q(parameter=par) & Q(projectparametervote__voter=user)).all()[0]
        np.value = params['value']
        if isinstance(params.get('caption'), basestring):
            np.caption = params['caption']
        np.save()
    return execute_conform_project_parameter({'psid' : params['psid'],
                                              'uuid' : par.uuid})
        
    
def execute_list_project_parameters(psid):
    """
    Arguments:
    - `psid`: psid as string
    """
    if Participant.objects.filter(psid=psid).count() == 0:
        return [u'There is no user with such psid'], httplib.NOT_FOUND
    proj = Project.objects.filter(participant__psid=psid).all()[0]
    ret = []
    for param in ProjectParameter.objects.filter(project=proj).all():
        p = {'uuid' : param.uuid,
             'name' : param.name,
             'descr' : param.descr,
             'tp' : param.tp,
             'enum' : param.tp}
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
        for vts in ProjectParameter.objects.filter(Q(parameter=param) & Q(status='voted')).all(): # проходим по предложенным значениям
            x = vts.projectparametervote_set.all()[0] # объект предложения
            v = {'uuid', x.voter.uuid,
                 'value', vts.value,
                 'caption', vts.caption,
                 'dt', vts.dt}
            votes.append(v)

        
        ret.append(p)
    return ret, httplib.OK
