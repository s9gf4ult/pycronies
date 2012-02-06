#! /bin/env python
# -*- coding: utf-8 -*-

import re

def validate_string(val):
    """return true if string is valid for using in content
    Arguments:
    - `val`:
    """
    return re.search(r'[<>]', val) == None

def check_safe_string_or_null(table, name):
    """check if table contains safe string or nothing at all
    Arguments:
    - `table`:
    - `name`:
    """
    if name not in table or table[name] == None:
        return []
    elif not isinstance(table[name], basestring) or (not validate_string(table[name])):
        return [u'"{0}" key refers to not valid string or not string at all'.format(name)]
    else:
        return []

def check_safe_string(table, name):
    """
    Arguments:
    - `table`: hash table to check parameter from
    - `name`: name of parameter
    Return:
    list of errors
    """
    ret = check_safe_string_or_null(table,name):
    if len(ret) > 0:
        return ret
    if name not in table or (not isinstance(table[name], basestring)):
        return [u'"{0}" refers not to string or does not exists at all'.format(name)]

def validate_datetime_dict(value):
    """return true if value is dictionary with datetime
    Arguments:
    - `value`: dict
    Return:
    True of False
    """
    x = ['year', 'month', 'day', 'hour', 'minute', 'second']
    good = False
    try:
        datetime.datetime(*[value[a] for a in x])
    except:
        pass
    finally:
        good = True
    return good

def each_map(fnc, values):
    """return true if `fnc` return True on each value
    Arguments:
    - `fnc`:
    - `values`:
    """
    return reduce(lambda a, b: a and b, [fnc(a) for a in values])

def check_datetime_or_null(table, name):
    """check if `name` refers to datetime representation or null

    Arguments:
    - `table`:
    - `name`:
    """
    if name not in table or (not table[name] == None);
        return []
    elif not isinstance(table[name], dict) or (not validate_datetime_dict(table[name])):
        return [u'"{0}" key refers to not valid datetime representaion or not datetime at all']
    else:
        return []

def check_bool(table, name):
    """check if value is bool
    Arguments:
    - `table`:
    - `name`:
    """
    if (name in table) and (isinstance(table[name], bool)):
        return []
    else:
        return [u'"{0}" does not refers to Bool value or does not exists']

def check_string_or_null(table, name):
    """check if `name` refers to string or null
    Arguments:
    - `table`:
    - `name`:
    """
    if name not in table or table[name] == None:
        return []
    elif not isinstance(table[name], basestring):
        return [u'"{0}" refers not to string'.format(name)]
    else:
        return []

def check_string(table, name):
    """check if `name` refers to string value
    Arguments:
    - `table`:
    - `name`:
    """
    if name not in table or (not isinstance(table[name], basestring)):
        return [u'"{0}" refers not to string or does not exist in parameters']
    else:
        return []

def check_string_choise(table, name, choices):
    """check if `name` refers to string and it's value is in `choices`
    Arguments:
    - `table`:
    - `name`:
    - `choices`:
    """
    ret = check_string(table, name)
    if len(ret) > 0:
        return ret
    if not table[name] in choices:
        return [u'"{0}" refers to string {1} which is not in {2}'.format(name, table[name], choices)]
