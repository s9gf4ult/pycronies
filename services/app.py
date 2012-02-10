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

def precheck_create_project(parameters):
    """check given parameters if they are correct
    Return list of errors found in parameters
    Arguments:
    - `parameters`:
    """
    ret = []
    if parameters == None or (not isinstance(parameters, dict)):
        return [u'You must give json coded dictionary']
    ret += check_safe_string(parameters, 'name')
    ret += check_safe_string_or_null(parameters, 'description')
    ret += check_datetime_or_null(parameters, 'begin_date')
    ret += check_bool(parameters, 'sharing')
    ret += check_string_choise(parameters, 'ruleset', [a[0] for a in Project.PROJECT_RULESET])
    ret += check_safe_string(parameters, 'user_name')
    ret += check_string_or_null(parameters, 'user_id')
    ret += check_safe_string_or_null(parameters, 'user_description')
    return ret

def execute_create_project(parameters):
    """create project and related objects based on parameters
    Arguments:
    - `parameters`: dict with parametes
    """
    p = Project(name = parameters['name'])
    if 'description' in parameters:
        p.description = parameters['description']
    if 'begin_date' in parameters:
        p.begin_date = dict2datetime(parameters['begin_date'])
    else:
        p.begin_date=datetime.now()
    if 'sharing' in parameters:
        p.sharing = parameters['sharing']
    if 'ruleset' in parameters:
        p.ruleset = parameters['ruleset']
    else:
        p.ruleset='despot'
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

def precheck_list_projects(props):
    """check properties and return list of errors
    Arguments:
    - `props`:
    """
    ret = []
    if props == None or (not isinstance(props, dict)):
        return [u'You must give json coded dictionary']
    ret += check_int_or_null(props, 'page_number')
    ret += check_int_or_null(props, 'projects_per_page')
    ret += check_string_choise_or_null(props, 'status', [a[0] for a in Project.PROJECT_STATUS])
    ret += check_datetime_or_null(props, 'begin_date')
    ret += check_safe_string_or_null(props, 'search')
    return ret

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

def precheck_create_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    ret = []
    ret += check_string(params, 'psid')
    ret += check_safe_string(params, 'name')
    ret += check_safe_string_or_null(params, 'descr')
    ret += check_string(params, 'tp')
    ret += check_bool(params, 'enum')
    ret += check_safe_string_or_null(params, 'value')
    ret += check_list_or_null(params, 'values')
    if len(ret) > 0:
        return ret
    if params['enum']:
        if params.get('values') == None:
            return ['"values" must be not null if "enum" is set']
        for vl in params['values']:
            if not isinstance(vl, dict):
                return [u'"values" must refer to list of dictionaries']
            ret += check_string(vl, 'value')
            ret += check_safe_string_or_null(vl, 'caption')
            if len(ret) > 0:
                return ret
    else:
        if not isinstance(params['value'], basestring)
    
    return ret

def execute_create_project_parameter(params):
    """
    Arguments:
    - `params`:
    """
    z


    
    # if Participant.objects.filter(psid=params['psid']).count() == 0:
    #     return [u'There is no participants with that psid'], httplib.NOT_FOUND
    # user = Participant.objects.filter(psid=params['psid']).all()[0]
    # if user.is_initiator==False:
    #     return [u'participant is not initiator of project'], httplib.PRECONDITION_FAILED
    # proj = Project.objects.get(participant=user)
    # if proj.ruleset != 'despot':
    #     return [u'ruleset of project must be "despot"'], httplib.PRECONDITION_FAILED

    # par = ProjectParameter(project=proj, name=params['name'],
    #                        tp=params['tp'], enum=params['enum'])
    # if params.get('descr') != None:
    #     par.descr = params['descr']
    # par.save()                  # создали параметр
    # if params.get('value') == None or (not isinstance(params['value'], basestring)):
    #     return [u'if "enum" is false then "value" must be set and be string'], httplib.PRECONDITION_FAILED
    # parval = ProjectParameterVal(parameter=par, status='accepted',
    #                              dt=datetime.now(), value=params['value'])
    # parval.save()               # создали и присвоили значение параметра
    # else:                       # множественное значение параметра
    #     if params.get('values') == None or (not isinstance(params['values'], list)):
    #         return [u'if "enum" is true then "values" must exists and be a list'], httplib.PRECONDITION_FAILED
    #     for val in params['values']: # проходим по множеству объектов
    #         if not isinstance(val, dict):
    #             return [u'"values" must be list of dictionaries, "{0}" met in this list'.format(val)], httplib.PRECONDITION_FAILED
    #         if 'value' not in val:
    #             return [u'"values" must be list of dictionaries with keys "value" and "caption", there is one dictionary withour "value" key'], httplib.PRECONDITION_FAILED
    #         enval = ProjectParameterVl(parameter=par, value=val['value'])
    #         if val.get('caption') != None and (not isinstance(val['caption'], basestring)):
    #             return [u'"values" must be list of dictionaries, each dictionary must contain field "caption" with string or do not at all, there is dictionaries with field "caption" not string'], httplib.PRECONDITION_FAILED
    #         if val.get('caption') != None and isinstance(val['caption'], basestring):
    #             enval.caption=val['caption']
    #         enval.save()
    #     return 'OK', httplib.CREATED
    
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
