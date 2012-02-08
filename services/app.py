#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import check_safe_string, check_safe_string_or_null, \
    check_datetime_or_null, check_bool, check_string, check_string_choise, \
    check_string_or_null, dict2datetime, check_int_or_null, check_string_choise_or_null, \
    datetime2dict
from services.models import Project, Participant, hex4, ParticipantVote, \
    DefaultProjectParameter, DefaultProjectParameterVl, ProjectParameter, ProjectParameterVl, ProjectParameterVal
from django.db import transaction
from django.db.models import Q
from datetime import datetime

def precheck_create_project(parameters):
    """check given parameters if they are correct
    Return list of errors found in parameters
    Arguments:
    - `parameters`:
    """
    ret = []
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

    pv = ParticipantVote(participant=pr, voter=pr, vote='include', status='accepted')
    pv.save()

    for param in DefaultProjectParameter.objects.filter((Q(ruleset=p.ruleset) | Q(ruleset=None)) & (Q(status=p.status) | Q(status=None))).all():
        projpar = ProjectParameter(project=p, default_parameter=param,
                                   name=param.name, descr=param.descr,
                                   tp=param.tp, enum=param.enum)
        projpar.save()
        if param.enum:          # перечисляемое значение, добавляем из таблицы значений по умолчанию
            for enums in DefaultProjectParameterVl.objects.filter(parameter=param).all():
                penum = ProjectParameterVl(parameter=projpar, value=enums.value, caption=enums.caption)
                penum.save()
        else:                   # значение одиночное, создаем запись со значением
            pval = ProjectParameterVal(parameter=projpar,
                                       value=param.default_value,
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
            return None
        else:
            return (fst & snd)
        
    qry = None                  # сформированное условие для отбора
    if props.get('status') != None:
        qry = none_and(qry, Q(status=props['status']))
    if props.get('begin_date') != None:
        qry = none_and(qry, Q(begin_date=props['begin_date']))
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
