#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import check_safe_string, check_safe_string_or_null, \
    check_datetime_or_null, check_bool, check_string, check_string_choise, check_string_or_null, dict2datetime
from services.models import Project, Participant, hex4
from django.db import transaction

def precheck_create_project(parameters):
    """check given parameters if they are correct
    Return list of errors found in parameters
    Arguments:
    - `parameters`:
    Acceptable keys are:
    - `name`: name of new project
    - `description`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `sharing` : Boolean
    - `ruleset` : string with ruleset name, may be 'despot'
    - `user_name` : string, name of user
    - `user_id` : external user id to bind participant with user
    - `user_description`: string, description of user. May be null
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
    Acceptable keys are:
    - `name`: name of new project
    - `description`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `sharing` : Boolean
    - `ruleset` : string with ruleset name, may be 'despot'
    - `user_name` : string, name of user
    - `user_id` : external user id to bind participant with user
    - `user_description`: string, description of user. May be null
    Return data in response body in json format:
    - `project_uuid` : string, universal identificator for project
    - `psid` : string, access key for new participant
    - `token` : string, access key for "magic link"
    """
    p = Project(name = parameters['name'])
    if 'description' in parameters:
        p.description = parameters['description']
    if 'begin_date' in parameters:
        p.begin_date = dict2datetime(parameters['begin_date'])
    if 'sharing' in parameters:
        p.sharing = parameters['sharing']
    if 'ruleset' in parameters:
        p.ruleset = parameters['ruleset']
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
    return {'project_uuid' : p.uuid,
            'psid' : pr.psid,
            'token' : pr.token}
