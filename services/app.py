#! /bin/env python
# -*- coding: utf-8 -*-

from services.common import check_safe_string, check_safe_string_or_null, \
    check_datetime_or_null, check_bool, check_string, check_string_choise, check_string_or_null
from services.models import Project

def precheck_create_project(parameters):
    """check given parameters if they are correct
    Return list of errors found in parameters
    Arguments:
    - `parameters`:
    Acceptable keys are:
    - `name`: name of new project
    - `description`: description of new project, may be null
    - `begin_date`: hash table with fields `year`, `month`, `day`, `hour`, `minute`, `second`. May be null
    - `shared` : Boolean
    - `ruleset` : string with ruleset name, may be 'despot'
    - `user_name` : string, name of user
    - `user_id` : external user id to bind participant with user
    - `user_description`: string, description of user. May be null
    """
    ret = []
    ret += check_safe_string(parameters, 'name')
    ret += check_safe_string_or_null(parameters, 'description')
    ret += check_datetime_or_null(parameters, 'begin_date')
    ret += check_bool(parameters, 'shared')
    ret += check_string_choise(parameters, 'ruleset', Project.PROJECT_RULESET)
    ret += check_safe_string(parameters, 'user_name')
    ret += check_string_or_null(parameters, 'user_id')
    ret += check_safe_string_or_null(parameters, 'user_description')
    return ret

def execute_create_project(parameters):
    """create project and related objects based on parameters
    Arguments:
    - `parameters`:
    """
    
