#! /bin/env python
# -*- coding: utf-8 -*-

import django.http as http
from django.db.models import Q
import httplib
import datetime
import re
import json
from functools import wraps
from svalidate import Validate
from services.statuses import PARAMETERS_BROKEN

yearmonthdayhour = ['year', 'month', 'day', 'hour', 'minute', 'second']
formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f']

def getencdec():
    """return json encoder and decoder
    """
    return (json.JSONEncoder(), json.JSONDecoder())

def dict2datetime(dct):
    """
    Arguments:
    - `dct`:
    """
    return datetime.datetime(*[dct[a] for a in yearmonthdayhour])

def string2datetime(val):
    """
    Arguments:

    - `val`:
    """
    ret = None
    for fmt in formats:
        try:
            ret = datetime.datetime.strptime(val, fmt)
        except ValueError:
            pass
        else:
            break
    if ret != None:
        return ret
    else:
        raise ValueError('Could not parse string as datetme')

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
    if table.get(name) == None:
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
    if isinstance(table.get(name), basestring) and validate_string(table[name]):
        return []
    else:
        return [u'"{0}" refers not to string or does not exists at all'.format(name)]

def validate_datetime_dict(value):
    """return true if value is dictionary with datetime
    Arguments:
    - `value`: dict
    Return:
    True of False
    """
    good = False
    try:
        datetime.datetime(*[value[a] for a in yearmonthdayhour])
    except:
        pass
    else:
        good = True
    return good

def each_map(fnc, values):
    """return True if `fnc` return True on each value

    Arguments:

    - `fnc`: function returning boolean and getting element from `values`
    - `values`: list of elements
    """
    return reduce(lambda a, b: a and b, [fnc(a) for a in values])

def check_datetime_or_null(table, name):
    """check if `name` refers to datetime representation or null

    Arguments:
    - `table`:
    - `name`:
    """
    if table.get(name) == None:
        return []
    elif isinstance(table[name], dict) and validate_datetime_dict(table[name]):
        return []
    else:
        return [u'"{0}" key refers to not valid datetime representaion or not datetime at all'.format(name)]

def check_bool(table, name):
    """check if value is bool
    Arguments:
    - `table`:
    - `name`:
    """
    if (name in table) and (isinstance(table[name], bool)):
        return []
    else:
        return [u'"{0}" does not refers to Bool value or does not exists'.format(name)]

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
        return [u'"{0}" refers not to string or does not exist in parameters'.format(name)]
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
    else:
        return []

def check_int_or_null(table, name):
    """check if name refers to int in table
    Arguments:
    - `table`:
    - `name`:
    """
    if table.get(name) == None:
        return []
    elif isinstance(table[name], int):
        return []
    else:
        return [u'"{0}" refers not to int'.format(name)]

def check_string_choise_or_null(table, name, values):
    """check if `name` references to string from `values`
    Arguments:
    - `table`:
    - `name`:
    - `values`:
    """
    if table.get(name) == None:
        return []
    elif isinstance(table[name], basestring) and (table[name] in values):
        return []
    else:
        return [u'key "{0}" references to "{1}" value, which does not belong to {2}'.format(name, table[name], values)]

def datetime2dict(value):
    """convert datetime to dictionary
    Arguments:
    - `value`:
    """
    return {'year' : value.year,
            'month' : value.month,
            'day' : value.day,
            'hour' : value.hour,
            'minute' : value.minute,
            'second' : value.second}

def json_request_handler(function):
    """wraps `function` with request parser
    first argument of `function` must be request method
    Arguments:
    - `function`:
    """
    @wraps(function)
    def ret(*args, **kargs):
        req = args[0]
        if req.method=='POST':
            enc, dec = getencdec()
            try:
                resp = dec.decode(req.read())
            except:
                return http.HttpResponse(status=httplib.PRECONDITION_FAILED, content=enc.encode(u'Could not parse content'))
            else:
                return function(*tuple([resp] + list(args[1:])), **kargs)

        else:
            return http.HttpResponse(status = httplib.NOT_IMPLEMENTED, content=u'You must use POST method here')
    return ret

def check_list_or_null(table, name):
    """
    Arguments:
    - `table`:
    - `name`:
    """
    if table.get(name) == None:
        return []
    if isinstance(table[name], list):
        return []
    else:
        return [u'key "{0}" references to {1} which is not list type'.format(name, table[name])]

class validate_params(object):
    """decrator for validating first paramter of function
    """

    def __init__(self, validator):
        """
        Arguments:
        - `validator`:
        """
        self._validator = validator

    def __call__(self, func):
        """
        """
        @wraps(func)
        def ret(*args, **kargs):
            params = args[0]
            enc = json.JSONEncoder()
            v = Validate()
            r = v.validate(self._validator,
                           params)
            if r != None:
                return http.HttpResponse(enc.encode(r), status=httplib.PRECONDITION_FAILED)
            return func(*args, **kargs)
        return ret

class standard_request_handler(object):
    """
    """
    white = re.compile(r'^\s*$')

    def __init__(self, validator):
        self._validator = validator

    def __call__(self, func):
        @wraps(func)
        def ret(*args, **kargs):
            request = args[0]
            if request.method != 'POST':
                return http.HttpResponse('You must use POST request, not {0}'.format(request.method), status=httplib.NOT_IMPLEMENTED, content_type='application/json')
            h = {}
            for key, value in request.POST.iteritems():
                if self.white.match(value) == None:
                    h[key] = value
            v = Validate()
            r = v.validate(self._validator, h)
            if r != None:
                enc = json.JSONEncoder()
                return http.HttpResponse(enc.encode({'code' : PARAMETERS_BROKEN,
                                                     'error' : r,
                                                     'caption' : 'Parameters of query is broken'}), status=httplib.PRECONDITION_FAILED, content_type='application/json')
            return func(*tuple([h] + list(args[1:])), **kargs)

        return ret

def get_or_create_object(objclass, findparams, setparams = {},
                         can_change = (lambda p: True),
                         can_use = (lambda p: True)):
    """
    Try to find object by findparams dictionary applying AND policy to find
    object with all fields (as keys) equal to values of this dictionary. If
    object has been found, then ensure values in `setparams` to be equal to the
    fields of that object. If object has not been found it is created and all
    fields set to values from `findparams` and `setparams`
    
    Arguments:
    
    - `objclass`: model class
    - `findparams`: fields to find with, dict
    - `setparams`: fields to set after found or creation, dict
    - `can_change`: one argument function checking that we can change
      existing object, if it return False and we need to change object the
      `get_or_create_object` return None
    - `can_use`: one argumeht function checking that we can use existing object
      return None emmediately
    """
    if len(findparams) == len([a for a in findparams.itervalues() if a != None]): # все параметры запроса установлены
        q = reduce(lambda a, b: a & b, [Q(**{key: val}) for (key, val) in findparams.iteritems()])
        if objclass.objects.filter(q).count() > 0: # есть объект который ищем
            obj = objclass.objects.filter(q).all()[0]
            if not can_use(obj):
                return None
            k = False
            ct = None
            for key, val in [(key, val) for (key, val) in setparams.iteritems() if val != None]: # выставляем значения если они не None
                if getattr(obj, key) != val:
                    if ct == None:
                        ct = can_change(obj)
                    if ct:
                        setattr(obj, key, val)
                        k = True
                    else:
                        return None
            if k:
                obj.save()
            return obj
    # если мы тут значит надо создать новый объект
    h = {}
    for dct in [findparams, setparams]:
        for key, val in dct.iteritems():
            if val != None:
                h[key] = val
    obj = objclass(**h)
    obj.save()
    return obj
