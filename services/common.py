#! /bin/env python
# -*- coding: utf-8 -*-

import django.http as http
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.sites.models import Site
from django.conf import settings
import django.core.mail
import httplib
import datetime
import re
import cgi
import json
from functools import wraps
from svalidate import Validate
from copy import copy
from services.statuses import PARAMETERS_BROKEN, ACCESS_DENIED, ACTIVITY_PARAMETER_NOT_FOUND, ACTIVITY_IS_NOT_ACCEPTED, \
    ACTIVITY_NOT_FOUND, RESOURCE_NOT_FOUND, ACTIVITY_RESOURCE_NOT_FOUND, ACTIVITY_RESOURCE_IS_NOT_ACCEPTED, RESOURCE_PARAMETER_NOT_FOUND
from services.models import Participant, Activity, ActivityParameter, parameter_class_map, DefaultParameterVl, Resource, \
    ActivityResourceParameter, ParticipantResourceParameter, User, hex4

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
            if request.method == 'POST':
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
            elif request.method == 'OPTIONS':
                r = http.HttpResponse()
                r['Allow'] = 'POST'
                return r
            else:
                return http.HttpResponse('You must use POST request, not {0}'.format(request.method), status=httplib.NOT_IMPLEMENTED, content_type='application/json')


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
                obj.save(force_update=True)
            return obj
    # если мы тут значит надо создать новый объект
    h = {}
    for dct in [findparams, setparams]:
        for key, val in dct.iteritems():
            if val != None:
                h[key] = val
    obj = objclass(**h)
    obj.save(force_insert=True)
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
    if get_object_status(user) == 'accepted':
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

class get_activity_from_uuid(object):
    def __init__(self, param = 'uuid'):
        self._param = param

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            params, user = args[:2]
            prj = user.project
            try:
                act = Activity.objects.filter(Q(project=prj) & Q(uuid=params[self._param])).all()[0]
            except IndexError:
                return {'code' : ACTIVITY_NOT_FOUND,
                        'caption' : 'There is no such actvivity'}, httplib.PRECONDITION_FAILED
            # ast = get_object_status(act)
            # if ast != 'accepted':
            #     return 'There is no one active status in this activity, posible error in some service', httplib.INTERNAL_SERVER_ERROR
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
        if ap.obj.project != prj:
            return {'code' : ACCESS_DENIED,
                    'caption' : 'Activity is not from your project'}, httplib.PRECONDITION_FAILED
        ast = get_object_status(ap.obj)
        if ast != 'accepted':
            return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                    'caption' : 'This activity is not accepted'}, httplib.PRECONDITION_FAILED
        return fnc(*tuple([params, ap, user] + list(args[2:])), **kargs)

    return ret

def get_or_create_object_parameter(obj, tpclass, unique, tp = 'text', name = None, descr = None, values = []):
    """
    Raises:

    - `TypeError`: if `obj` is not model with parameters
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('obj not the model instance with parameters')

    pclass = parameter_class_map[t]['param']
    q = Q(obj=obj) & Q(tpclass = tpclass)
    if tpclass == 'user':
        if not isinstance(name, basestring):
            raise Exception('name must be string if tpclass == "user", not {0}'.format(name))
        q &= Q(name=name)
    try:
        prmt = pclass.objects.filter(q).all()[0]
    except IndexError:
        return create_object_parameter(obj, tpclass, unique, tp, name, descr, values)
    return prmt

def create_object_parameter(obj, tpclass, unique, tp = 'text', name = None, descr = None, values = []):
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

    Raises:

    - `TypeError`: if obj is wrong type
    - `IntegrityError`: if this such parameter is alreary exists
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('obj must be one of model classes with parametes, not {0}'.format(t))
    pclass = parameter_class_map[t]['param']
    pvlclass = parameter_class_map[t]['vl']
    prmt = pclass(obj = obj,
                  tpclass = tpclass,
                  unique = 1 if unique else None,
                  tp = tp,
                  name = name,
                  enum = (True if (len(values) > 0) else False),
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
    return prmt

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
    set_object_parameter(obj, user, newstatus, tpclass = 'status', comment = comment)

def set_object_parameter(obj, user, value, uuid = None, tpclass = None, name = None, caption = None, dt = None, comment = None):
    """
    Arguments:

    - `obj`:
    - `user`: Participant, which set object parameter
    - `value`: new value to set
    - `uuid`: uuid of parameter, if not None then `tpclass` and `name` are ignored
    - `tpclass`: typeclass for example 'status'
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

    q = Q(value=value) & Q(status='accepted') & Q(parameter__obj=obj)
    if isinstance(uuid, basestring):
        q &= Q(parameter__uuid=uuid)
    else:
        q &= Q(parameter__tpclass = tpclass)
        if tpclass == 'user' :
            q &= Q(parameter__name = name)
    if pvalclass.objects.filter(q).count() > 0: # there is one value set already
        return

    qf = Q(obj = obj)
    if isinstance(uuid, basestring):
        qf &= Q(uuid=uuid)
    else:
        qf &= Q(tpclass = tpclass)
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
                    status = 'accepted')
    if caption != None:
        val.caption = caption
    if dt != None:
        val.dt = dt
    pvalclass.objects.filter(parameter = param,
                             status='accepted').update(status='changed')
    val.save(force_insert=True)
    # set vote for it
    if voteclass != None:
        vote = voteclass(voter = user,
                         parameter_val = val)
        if comment != None:
            vote.comment = comment
        vote.save(force_insert=True)

def create_object_parameter_from_default(obj, default):
    """
    Creates user parameter (tpclass = 'user') with name and other parameters
    given from `default`

    Arguments:

    - `obj`:
    - `default`: object of default parameter

    Raises:

    - `TypeError`: if obj is wrong typed
    - `IntegriryError` if default parameter correlate with existing parameters
    """
    values = []
    if default.enum:
        for v in DefaultParameterVl.objects.filter(parameter=default).all():
            values.append({'value' : v.value,
                           'caption' : v.caption})
    return create_object_parameter(obj, 'user', False,
                                   tp = default.tp,
                                   name=default.name,
                                   descr=default.descr,
                                   values=values)

def get_object_status(obj):
    """
    Return current value of status

    Arguments:
    - `obj`:
    """
    return get_object_parameter(obj, 'status')

def get_object_parameter(obj, tpclass, name = None):
    """
    Return None if there is no one parameter found or if there is no one
    "accepted" value for found parameter, otherwise reurn "accepted" value of
    parameter.

    Arguments:
    - `obj`:
    - `tpclass`:
    - `name`: user parameter if tpclass == 'user'

    Raises:

    - `TypeError`: if `obj` has wrong class
    - `Exception`: if `tpclass` == "user" and name is not defined
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('obj must be instance of model class with properties, not {0}'.format(t))
    pclass = parameter_class_map[t]['param']
    pvalclass = parameter_class_map[t]['val']
    q = Q(status='accepted') & Q(parameter__tpclass=tpclass) & Q(parameter__obj=obj)
    if tpclass == 'user':
        if not isinstance(name, basestring):
            raise Exception('if tpclass == "user" then name must be set')
        q &= Q(parameter__name = name)
    try:
        prm = pvalclass.objects.filter(q).all()[0]
    except IndexError:
        return None
    return prm.value

def set_vote_for_object_parameter(obj, user, value, uuid = None, tpclass = None, name = None, comment = None, caption = None):
    """
    Add vote for object parameter if it does not exists, otherwise
    add vote for existing value

    Arguments:

    - `obj`:
    - `user`:
    - `value`:
    - `uuid`: if uuid is given then tpclass and name is ignored
    - `name`:
    - `tpclass`: if tpclass is 'user' then `name` is required
    - `comment`:
    - `caption`:

    Raises:

    - `TypeError`: if `obj` is not model with properties
    - `Exception`: if `name` is not string and `tpclass' == 'user'
    - `IndexError`: if there is no one suitable parameter
    - `AttributeError`: if parameter can not be voted
    - `ValueError`: If value can not be accepted to enum parameter
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('obj has wrong type {0}'.format(t))

    pclass = parameter_class_map[t]['param']
    pvalclass = parameter_class_map[t]['val']
    pvlclass = parameter_class_map[t]['vl']
    pvoteclass = parameter_class_map[t].get('vote')

    if isinstance(uuid, basestring):
        q = Q(uuid=uuid) & Q(obj=obj)
    else:
        q = Q(obj=obj) & Q(tpclass=tpclass)
        if tpclass == 'user':
            if not isinstance(name, basestring):
                raise Exception('name must be string when tpclass == "user"')
            q &= Q(name=name)
    # get parameter
    prm = pclass.objects.filter(q).all()[0]
    if prm.enum:
       if pvlclass.objects.filter(Q(value=value) & Q(parameter=prm)).count() == 0:
           raise ValueError('this value can not be accepted')

    # get or create voted value
    pval = get_or_create_object(pvalclass,
                                {'parameter' : prm,
                                 'value' : value,
                                 'status' : 'voted'},
                                {'caption' : caption},
                                can_change = (lambda a: False))
    # delete all other votes for values of this parameter
    pvoteclass.objects.filter(Q(voter=user) &
                              Q(parameter_val__status='voted') &
                              Q(parameter_val__parameter=prm)).delete()
    # create vote for our value
    vt = pvoteclass(voter=user,
                    parameter_val=pval)
    if isinstance(comment, basestring):
        vt.comment = comment
    vt.save(force_insert=True)


def get_vote_value_for_object_parameter(obj, user, uuid = None, tpclass = None, name = None):
    """Return object's parameter's value model object for whitch user has voted

    If there is no one value voted, then return None

    Raises:

    - `TypeError`: if `obj` is not a model with parameters
    - `Exception`: if `tpclass` == 'user' and `name` is not a string
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError('type of the object must be model with parameters, not {0}'.format(t))

    valclass = parameter_class_map[t]['val']
    voteclass = parameter_class_map[t]['vote']
    q = Q(status='voted') & Q(parameter__obj=obj) & Q(**{'{0}__voter'.format(voteclass.__name__.lower()) : user})
    if isinstance(uuid, basestring):
        q &= Q(parameter__uuid = uuid)
    else:
        q &= Q(parameter__tpclass=tpclass)
        if tpclass == 'user':
            if not isinstance(name, basestring):
                raise Exception('name must be string if tpclass == "user"')
            q &= Q(parameter__name=name)
    try:
        ret = valclass.objects.filter(q).all()[0]
    except IndexError:
        return None
    return ret

def set_as_accepted_value_of_object_parameter(val): #  FIXME: надо проверять enum параметр перед назначением
    """
    Waring ! this does not check value can be set for enumerable parameters

    Arguments:
    - `val`: value object

    Raises:

    """
    prm = val.parameter
    type(val).objects.filter(Q(status='voted') & Q(parameter=prm)).update(status='wasvoted')
    type(val).objects.filter(Q(status='accepted') & Q(parameter=prm)).update(status='changed')
    val.status='accepted'
    val.save(force_update=True)

class get_resource_from_uuid(object):
    def __init__(self, param = 'uuid'):
        self._param = param

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            (params, act, user) = args[:3]
            prj = user.project
            try:
                res = Resource.objects.filter(uuid = params[self._param]).all()[0]
            except IndexError:
                return {'code' : RESOURCE_NOT_FOUND,
                        'caption' : 'There is no such resource'}, httplib.PRECONDITION_FAILED
            if res.project != prj:
                return {'code' : ACCESS_DENIED,
                        'caption' : 'You can not use this resource'}, httplib.PRECONDITION_FAILED
            return fnc(*tuple([params, res, act, user] + list(args[3:])), **kargs)

        return ret

def get_activity_resource_from_parameter(fnc):
    @wraps(fnc)
    def ret(*args, **kargs):
        (params, res, act, user) = args[:4]
        try:
            ares = res.activityresource_set.filter(activity=act).all()[0]
        except IndexError:
            return {'code' : ACTIVITY_RESOURCE_NOT_FOUND,
                    'caption' : 'This resource is not using in this activity'}, httplib.PRECONDITION_FAILED
        return fnc(*tuple([params, ares, res, act, user] + list(args[4:])), **kargs)

    return ret

def check_activity_resource_status(fnc):
    @wraps(fnc)
    def ret(*args, **kargs):
        (params, ares) = args[:2]
        st = get_object_status(ares)
        if st == 'accepted':
            return fnc(*args, **kargs)
        else:
            return {'code' : ACTIVITY_RESOURCE_IS_NOT_ACCEPTED,
                    'caption' : 'This resource is not accepted on this activity'}, httplib.PRECONDITION_FAILED
    return ret

def get_authorized_activity_participant(user, activ):
    try:
        ap = activ.activityparticipant_set.filter(participant = user).all()[0]
    except IndexError:
        return None
    st = get_object_status(ap)
    if st == 'accepted' or am_i_creating_activity_now(activ, user):
        return ap
    else:
        return False

def am_i_creating_activity_now(act, user):
    return get_object_status(act) == 'created' and (user in get_parameter_voter(act, 'accepted', 'created', tpclass = 'status'))


class get_resource_parameter_from_uuid(object):
    """
    Decorator gets activity resource parameter from parameters in (as first
    argument of decorated function) and insert it as second parameter of
    decorated function. Resource parameter may be the parameter of
    ActivityResource or ParticipantResource as well, depending on type of
    resource usage
    Check authorization of activity participant too
    """
    def __init__(self, param = 'uuid'):
        self._param = param

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            params, user = args[:2]
            try:
                aresp = ActivityResourceParameter.objects.filter(Q(uuid=params[self._param])).all()[0]
            except IndexError:
                try:
                    aresp = ParticipantResourceParameter.objects.filter(uuid = params[self._param]).all()[0]
                except IndexError:
                    return {'code' : RESOURCE_PARAMETER_NOT_FOUND,
                            'caption' : 'There is no such resource parameter'}, httplib.PRECONDITION_FAILED

            if isinstance(aresp, ActivityResourceParameter):
                ares = aresp.obj
            else:
                ares = aresp.obj.resource

            if get_object_status(ares) != 'accepted':
                return {'code' : ACTIVITY_RESOURCE_IS_NOT_ACCEPTED,
                        'caption' : 'This resource is not accepted on this activity'}, httplib.PRECONDITION_FAILED
            act = ares.activity
            if get_object_status(act) != 'accepted':
                return {'code' : ACTIVITY_IS_NOT_ACCEPTED,
                        'caption' : 'This activity is not accepted'}, httplib.PRECONDITION_FAILED
            ap = get_authorized_activity_participant(user, act)
            if ap == None or ap == False:
                return {'code' : ACCESS_DENIED,
                        'caption' : 'You are not acvitity participant'}, httplib.PRECONDITION_FAILED
            return fnc(*tuple([params, aresp, user] + list(args[2:])), **kargs)
        return ret

class translate_parameters(object):
    def __init__(self, phash):
        self._phash = phash

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            params = args[0]
            pp = copy(params)
            for k, fn in self._phash.items():
                if pp.get(k) != None:
                    pp[k] = fn(pp[k])
            return fnc(*tuple([pp] + list(args[1:])), **kargs)
        return ret

def parse_json(data):
    dec = json.JSONDecoder()
    return dec.decode(data)

def get_parameter_voter(obj, status, value, tpclass = None, name = None ,uuid = None):
    """
    Return list of voters, which voted for specified value with specified status
    of specified parameter

    Arguments:

    - `obj`:
    - `status`:
    - `value`:
    - `tpclass`:
    - `name`:
    - `uuid`:

    Raises:

    - `TypeError`: if obj has wrong type
    - `ValueError`: if something wrong with parameters
    """
    t = type(obj)
    if t not in parameter_class_map:
        raise TypeError("obj must be model object with parameters, not {0}".format(t))
    vote = parameter_class_map[t]['vote']
    q = (Q(parameter_val__parameter__obj = obj)&
         Q(parameter_val__status = status)&
         Q(parameter_val__value = value))
    if uuid != None:
        q &= Q(parameter_val__parameter__uuid = uuid)
    else:
        if tpclass == 'user':
            if not isinstance(name, basestring):
                raise ValueError('You must specify `name` of parameter, if tpclass == "user"')
        elif not isinstance(tpclass, basestring):
            raise ValueError('You must specify `tpclass` if `uuid` is not specified')
        q &= Q(parameter_val__parameter__tpclass = tpclass)
        if name != None:
            q &= Q(parameter_val__parameter__name = name)

    ret = []
    for vt in vote.objects.filter(q).distinct().all():
        ret.append(vt.voter)
    return ret

def translate_string(string):
    return cgi.escape(string, True)

def translate_values(string):
    dec = json.JSONDecoder()
    d = dec.decode(string)
    if not isinstance(d, list):
        raise ValueError('translate_values: Json parsed data is not a list')
    for vl in d:
        if not isinstance(vl, dict):
            raise ValueError('translate_values: Element of list is not a dictionary, but must be')
        if vl.get('caption') != None:
            vl['caption'] = translate_string(vl['caption'])
    return d

class proceed_checks(object):
    """check decorator
    """
    enc = json.JSONEncoder()

    def __init__(self, *check_functions):
        for fn in check_functions:
            if not callable(fn['lambda']):
                raise TypeError('proceed_checks: all values with key "lambda" must be callable objects')
            if not isinstance(fn['caption'], basestring):
                raise TypeError('proceed_checks: all values with key "caption" must be strings')
        self._check_functions = check_functions

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            params = args[0]
            for chck in self._check_functions:
                if not chck['lambda'](params):
                    return http.HttpResponse(self.enc.encode({'code' : PARAMETERS_BROKEN,
                                                              'caption' : chck['caption']}),
                                             status = httplib.PRECONDITION_FAILED,
                                             content_type = 'application/json')
            return fnc(*args, **kargs)
        return ret

class naive_json_responder(object):
    """
    """
    enc = json.JSONEncoder()

    def __init__(self, handler):
        if not callable(handler):
            raise TypeError('naive_json_responder: parameter must be callable object')
        self._handler = handler

    def __call__(self, fnc):
        @wraps(fnc)
        def ret(*args, **kargs):
            ret, stat = self._handler(*args, **kargs)
            return http.HttpResponse(self.enc.encode(ret),
                                     status = stat,
                                     content_type = 'application/json')
        return ret

def create_user(email, password, name, descr = None):
    """
    Arguments:

    - `email`:
    - `password`:
    - `name`:
    - `descr`:
    """
    a = {'email' : email,
         'password' : make_password(password),
         'name' : name}
    if descr != None:
        a['descr'] = descr
    user = User(**a)
    user.save(force_insert=True)
    return user

def get_database_user(email, password):
    """
    Arguments:

    - `email`:
    - `password`:
    """
    try:
        u = User.objects.filter(email = email).all()[0]
    except IndexError:
        return None
    if check_password(password, u.password):
        return u
    else:
        return None

def get_acceptable_user(email, password):
    """
    Arguments:

    - `email`:
    - `password`:
    """
    u = get_database_user(email, password)
    if u != None and u.is_active:
        return u
    else:
        return None

def auth_user(email, password):
    u = get_acceptable_user(email, password)
    if u == None:
        return None
    u.token = hex4()
    u.save(force_update = True)
    return u

def generate_user_magic_link(magicpath, magicid):
    """

    Arguments:
    - `user`:
    """
    site = Site.objects.get_current()
    return '{0}://{1}{2}/{3}/{4}'.format(settings.MY_PROTOCOL_NAME,
                                         site.domain,
                                         ':{0}'.format(settings.MY_PORT) if settings.MY_PORT != 80 else '',
                                         magicpath,
                                         magicid)

def send_mail(*args, **kargs):
    """
    Arguments:
    
    - `subject`:
    - `message`:
    - `from_email`:
    - `recipient_list`:
    - `fail_silently`:
    - `auth_user`:
    - `auth_password`:
    - `connection`:
    """
    if settings.EMAIL_DO_REALY_SEND:
        return django.core.mail.send_mail(*args, **kargs)
    else:
        print('Just simulate real sending email to {0}'.format(args[3]))
        return None

def get_registered_user(psid):
    """
    Arguments:
    
    - `psid`:
    """
    try:
        u = User.objects.filter(participant__psid = psid).all()[0]
    except IndexError:
        return None
    return u

def return_if_debug(data, normal_mode_data = ''):
    if settings.DEBUG:
        return data
    else:
        return normal_mode_data
