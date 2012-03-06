#! /bin/env python
# -*- coding: utf-8 -*-

import django.http as http
from django.db.models import Q
from django.db import transaction
import httplib
import datetime
import re
import json
from functools import wraps
from svalidate import Validate
from services.statuses import PARAMETERS_BROKEN, ACCESS_DENIED, ACTIVITY_PARAMETER_NOT_FOUND, ACTIVITY_IS_NOT_ACCEPTED
from services.models import Participant, Activity, ActivityParameter, parameter_class_map

yearmonthdayhour = ['year', 'month', 'day', 'hour', 'minute', 'second']
formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f']

def getencdec():
    """return json encoder and decoder
    """
    return (json.JSONEncoder(), json.JSONDecoder())


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


class standard_request_handler(object):
    """
    """
    white = re.compile(r'^\s*$')
    v = Validate()

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
            r = self.v.validate(self._validator, h)
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


def get_authorized_user(p):
    """
    Return None if there is no user

    Return False if user has no 'accepted' status

    Otherwise return user itself

    Arguments:

    - `p`: string with user `psid`
    """
    if Participant.objects.filter(psid=p).count() == 0:
        return None
    user = Participant.objects.filter(psid=p).all()[0]
    if user.participantstatus_set.filter(Q(status='accepted') & Q(value='accepted')).count() > 0:
        return user
    return False


def get_user(fnc):
    """
    Wraps function with user picker
    
    Arguments:
    
    - `fnc`:
    """
    @wraps(fnc)
    def ret(*args, **kargs):
        params = args[0]
        user = get_authorized_user(params['psid'])
        if user == None:
            return u'There is no user with that psid', httplib.NOT_FOUND
        if user == False:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'You are not authorized user to do that'}, httplib.PRECONDITION_FAILED
        return fnc(*tuple([params, user] + list(args[1:])), **kargs)
    return ret

class get_object_by_uuid(object):
    """Try to get object by uuid in parameters
    """
    
    def __init__(self, modelclass, code, caption):
        self._modelclass = modelclass
        self._code = code
        self._caption = caption

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            params = args[0]
            if self._modelclass.objects.filter(uuid=params['uuid']).count() == 0:
                return {'code' : self._code,
                        'caption' : self._caption}, httplib.PRECONDITION_FAILED
            obj = self._modelclass.objects.filter(uuid=params['uuid']).all()[0]
            return fnc(*tuple([params, obj] + list(args[1:])), **kargs)
        return ret

class typical_json_responder(object):
    enc = json.JSONEncoder()
    
    def __init__(self, executor, normal_status):
        if not callable(executor):
            raise ValueError('executor must be callable')
        self._executor = executor
        self._normal_status = normal_status

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            val, st = self._executor(*args, **kargs)
            if st != self._normal_status:
                transaction.rollback()
            return http.HttpResponse(self.enc.encode(val), status=st, content_type='application/json')

        return ret

def get_activity_from_uuid(fnc):
    @wraps(fnc)
    def ret(*args, **kargs):
        params, user = args[:2]
        prj = user.project
        if Activity.objects.filter(Q(project=prj) & Q(uuid=params['uuid'])).count() == 0:
            return {'code' : ACTIVITY_NOT_FOUND,
                    'caption' : 'There is no such actvivity'}, httplib.PRECONDITION_FAILED
        act = Activity.objects.filter(uuid=params['uuid']).all()[0]
        if act.activitystatus_set.filter(status='accepted').count() == 0:
            return 'There is no one active status in this activity, posible error in some service', httplib.INTERNAL_SERVER_ERROR
        return fnc(*tuple([params, act, user] + list(args[2:])), **kargs)
    return ret

def get_activity_parameter_from_uuid(fnc):
    @wraps(fnc)
    def ret(*args, **kargs):
        params, user = args[:2]
        prj = user.project
        if ActivityParameter.objects.filter(uuid=params['uuid']).count() == 0:
            return {'code' : ACTIVITY_PARAMETER_NOT_FOUND,
                    'caption' : 'Activity parameter did not found'}, httplib.PRECONDITION_FAILED
        ap = ActivityParameter.objects.filter(uuid=params['uuid']).all()[0]
        if ap.activity.project != prj:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'Activity is not from your project'}, httplib.PRECONDITION_FAILED
        elif ap.activity.activitystatus_set.filter(Q(status='accepted') & Q(value='accepted')).count() == 0:
            return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                    'caption' : 'This activity is not accepted'}, httplib.PRECONDITION_FAILED
        return fnc(*tuple([params, ap, user] + list(args[2:])), **kargs)

    return ret

def create_object_parameter(obj, tpclass, unique, tp = None, name = None, descr = None, values = []):
    """
    Universal object parameter creator
    
    Arguments:
    
    - `obj`: object of model class with parameters
    - `tpclass`: typeclass, for example 'status' or 'user'
    - `unique`: True if there is just one parameter for given typeclass can be
    - `tp`: type for user parameters
    - `name`: name for user parameters
    - `descr`: descritpion
    - `values`: list of posible parameters
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise ValueError('obj must be one of model classes with parametes, not {0}'.format(t))
    pclass = parameter_class_map[t]['param']
    pvlclass = parameter_class_map[t]['vl']
    prmt = pclass(obj = obj,
                  tpclass = tpclass,
                  unique = 1 if unique else None,
                  tp = tp,
                  name = name,
                  enum = True if len(values) > 0 ele False,
                  descr = descr)
    prmt.save(force_insert=True)
    for vl in values:
        pvl = pvlclass(parameter = prmt,
                       value = vl['value'],
                       caption = vl.get('caption'))
        try:
            pvl.save(force_insert=True)
        except IntegrityError:
            pass                # just ignore same values
        
def set_object_status(obj, user, newstatus, comment = None):
    """
    Arguments:
    
    - `obj`:
    - `user`: user which changes the status
    - `newstatus`:
    - `comment`: user comment
    
    Raises:

    - `IndexError`: if there is no such parameter
    - `TypeError`: when given `obj` is not model class which has parameters
    - `ValueError`: when given value can not be set for this parameter
    """
    set_object_parameter(obj, user, 'status', newstatus, comment = comment)

def set_object_parameter(obj, user, tpclass, value, name = None, caption = None, dt = None, comment = None):
    """
    Arguments:
    
    - `obj`:
    - `user`: Participant, which set object parameter
    - `tpclass`: typeclass for example 'status'
    - `value`: new value to set
    - `name`: name of user parameter if `tpclass` == 'user'
    - `caption`: caption for this value
    - `dt`: datetime for parameter activation
    - `comment`: user comment

    Raises:

    - `IndexError`: if there is no such parameter
    - `TypeError`: when given `obj` is not model class which has parameters
    - `ValueError`: when given value can not be set for this parameter
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('obj must be model type with parameters, not {0}'.format(t))
    pclass = parameter_class_map[t]['param']
    pvalclass = parameter_class_map[t]['val']
    pvlclass = parameter_class_map[t]['vl']
    voteclass = parameter_class_map[t].get('vote')
    q = Q(value=value) & Q(status='accepted') & Q(parameter__obj=obj) & Q(parameter__tpclass = tpclass)
    if tpclass == 'user' :
        q &= Q(parameter__name = name)
    if pvalclass.objects.filter(q).count() > 0: # there is one value set already
        return
    qf = Q(obj = obj) & Q(tpclass = tpclass)
    if tpclass == 'user':
        qf &= Q(name=name)
    # got parameter
    param = pclass.objects.filter(qf).all()[0]
    # check value before set if needed
    if param.enum:
        if pvlclass.objects.filter(Q(parameter=param) & Q(value=value)).count() == 0:
            raise ValueError('value can not be set for this parameter')
    # set value
    val = pvalclass(parameter = param,
                    value = value,
                    caption = caption,
                    dt = dt,
                    status = 'accepted')
    pvalclass.objects.filter(parameter = param,
                             status='accepted').update(status='changed')
    val.save(force_insert=True)
    # set vote for it
    if voteclass != None:
        vote = voteclass(voter = user,
                         comment = comment,
                         parameter_val = val)
        vote.save(force_insert=True)

def create_object_parameter_from_default(obj, default):
    """
    Arguments:
    
    - `obj`:
    - `default`:
    """
    
    pass
