#!/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main
import httplib, urllib
import json
from services.statuses import *
import datetime
import random

host = '127.0.0.1'
port = 8000

def fnone(arg):
    ret = {}
    for a, b in arg.iteritems():
        if b != None:
            ret[a] = b
    return ret

def getencdec():
    """
    """
    return (json.JSONEncoder(), json.JSONDecoder())

def encodeparams(prms):
    return urllib.urlencode(prms, 'utf-8')

def request(conn, route, data):
    conn.request('POST', route, encodeparams(data), {'Content-Type' : 'application/x-www-form-urlencoded; charset=utf-8'})

def string2datetime(val):
    """
    Arguments:

    - `val`:
    """
    formats = ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S.%f']

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

def filterNone(data):
    ret = {}
    for k, v in data.iteritems():
        if v != None:
            ret[k] = v
    return ret
    

class common_test(TestCase):

    def srequest(self, conn, route, data, status=None, print_result=False, get_status = False):
        dec = json.JSONDecoder()
        request(conn, route, filterNone(data))
        r = conn.getresponse()
        ret = r.read()
        if print_result:
            try:
                print('>>>>>>>>> response to {0}:\n{1}'.format(route, dec.decode(ret)))
            except:
                print('>>>>>>>>> failed to parse response to {0}:\n{1}'.format(route, ret))
        if status != None:
            self.assertEqual(r.status, status)
        if get_status:
            return ret, r.status
        else:
            return ret

    def _logout(self, token, evidence = 201, print_error = False):
        """
        """
        c = httplib.HTTPConnection(host, port)
        return self.srequest(c, '/services/user/logout', {'token' : token}, status = evidence, print_result = print_error)
        

    def _delete_project(self, psid):
        """
        Arguments:
        - `psid`:
        """
        c = httplib.HTTPConnection(host, port)
        request(c, '/services/project/delete', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)

    def _get_authenticated_user(self, email, password, name, print_error = False):
        ret, st = self._user_check(email, evidence = None, print_error = print_error)
        if st == 200:
            ret = self._authenticate_user(email, password, print_error = print_error)
            token = ret['token']
        elif st == 404:
            self._create_user_account(email, password, name, print_error = print_error)
            ret = self._ask_user_confirmation(email, print_error = print_error)
            self._confirm_account(email, password, ret['confirmation'], print_error = print_error)
            ret = self._authenticate_user(email, password, print_error = print_error)
            token = ret['token']
        else:
            print("fuck ! Status is {0}".format(st))
            assert(False)
        return token

    def _auth_user_and_get_project(self,
                                   project_name = 'project1',
                                   project_descr = None,
                                   sharing = 'open',
                                   ruleset = 'despot',
                                   project_user_name = 'root',
                                   email = 'root@mail.ru',
                                   password = '123',
                                   name = 'root',
                                   print_error = False):
        """Get many arguments and return tuple of token, psid, and project uuid"""
        token = self._get_authenticated_user(email, password, name, print_error = print_error)
        ret = self._create_project(name = project_name,
                                   descr = project_descr,
                                   sharing = sharing,
                                   ruleset = ruleset,
                                   user_name = project_user_name,
                                   user_id = token,
                                   print_error = print_error)
        return (token,) + ret

    def _create_activity(self, psid, name = 'default', begin = '2010-10-10 10:10:10', end = '2010-10-11 10:10:10', descr = None, evidence = 201, print_error = False):
        """
        return uuid of new activity
        """
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        ret = self.srequest(c, '/services/activity/create',
                            {'psid' : psid,
                             'name' : name,
                             'descr' : descr,
                             'begin' : begin,
                             'end' : end}, status = evidence, print_result = print_error)
        if evidence == 201:
            return dec.decode(ret)['uuid']
        else:
            return ret

    def _public_activity(self, psid, uuid, comment = None, evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid,
                       'uuid' : uuid,
                       'comment' : comment},
                      status = evidence, print_result = print_error)

    def _list_activities(self, psid = None, uuid = None, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid,
                           'uuid' : uuid},
                          status = evidence, print_result = print_error)
        if evidence == 200:
            return dec.decode(r)
        else:
            return r
        
            
    def _create_project(self,
                        name = 'project1',
                        descr = None,
                        sharing = 'open',
                        ruleset = 'despot',
                        user_name = 'root',
                        user_id = None,
                        evidence = httplib.CREATED,
                        print_error = False
                        ):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/project/create',
                          fnone({'name' : name,
                                 'descr' : descr,
                                 'sharing' : sharing,
                                 'ruleset' : ruleset,
                                 'user_name' : user_name,
                                 'user_id' : user_id}),
                          status = evidence, print_result = print_error)
        d = dec.decode(r)
        return d['psid'], d['uuid']

    def _set_project_status(self, psid, status, comment = None, evidence = httplib.CREATED, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/project/status/change',
                      fnone({'psid' : psid,
                             'status' : status,
                             'comment' : comment}),
                      status = evidence, print_result = print_error)

    def _user_check(self, email, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        return self.srequest(c, '/services/user/check',
                             fnone({'email' : email}),
                             status = evidence, get_status = True, print_result = print_error)

    def _token_check(self, token, evidence, print_error = False):
        c = httplib.HTTPConnection(host, port)
        return self.srequest(c, '/services/token/check',
                             {'token': token},
                             status = evidence, print_result = print_error)
    

    def _create_user_account(self, email, password, name, evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/user/new',
                          fnone({'email' : email,
                                 'password' : password,
                                 'name' : name}),
                          status = evidence, print_result = print_error)
        d = dec.decode(r)
        return d

    def _ask_user_confirmation(self, email, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/user/ask_confirm',
                          fnone({'email' : email}),
                          status = evidence, print_result = print_error)
        d = dec.decode(r)
        return d

    def _authenticate_user(self, email, password, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/user/auth',
                          fnone({'email' : email,
                                 'password' : password}),
                          status = evidence, print_result = print_error)
        d = dec.decode(r)
        return d

    def _confirm_account(self, email, password, confirmation, evidence = 202, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/user/confirm',
                      fnone({'email' : email,
                             'password' : password,
                             'confirmation' : confirmation}),
                      status = evidence, print_result = print_error)

    def _enter_open_project(self, uuid, name, descr = None, user_id = None, evidence = 201, print_error = False):
        """Eneter to open project and return psid and auth token"""
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/project/enter/open',
                          {'uuid' : uuid,
                           'name' : name,
                           'descr' : descr,
                           'user_id' : user_id}, status = evidence, print_result = print_error)
        if evidence == 201:
            d = dec.decode(r)
            return d['psid'], d['token']
        else:
            return r

    def _list_projects(self, page_number = 0, projects_per_page = None,
                       status = None, participants = None,
                       begin_date = None,
                       search = None, uuid = None,
                       evidence = 200, print_error = False):
        """Return Projects list and pages count"""
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/project/list',
                          {'page_number' : page_number,
                           'projects_per_page' : projects_per_page,
                           'status' : status,
                           'participants' : participants,
                           'begin_date' : begin_date,
                           'search' : search,
                           'uuid' : uuid},
                          status = evidence, print_result = print_error)
        if evidence == 200:
            d = dec.decode(r)
            return d['projects'], d['pages']
        else:
            return r

    def _exit_project(self, token, uuid, evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/project/exit',
                      {'token' : token,
                       'uuid' : uuid},
                      status = evidence, print_result = print_error)

    def _check_project_participation(self, token, uuid, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/project/participation/check',
                      {'token' : token,
                       'uuid' : uuid},
                      status = evidence, print_result = print_error)

    def _change_project_status(self, psid, status, evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'status' : status},
                      status = evidence, print_result = print_error)

    def _list_participants(self, psid = None, uuid = None, evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/participant/list',
                          {'psid' : psid,
                           'uuid' : uuid},
                          status = evidence, print_result = print_error)
        if evidence == 200:
            return dec.decode(r)
        else:
            return r

    def _create_project_resource(self, psid, name = 'resource1', descr = None,
                                 units = 'kg', use = 'common', site = 'external',
                                 evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid,
                           'name' : name,
                           'descr' : descr,
                           'units' : units,
                           'use' : use,
                           'site' : site},
                          status = evidence, print_result = print_error)
        if evidence == 201:
            return dec.decode(r)['uuid']
        else:
            return r

    def _include_activity_resource(self, psid, activity, uuid, need = False,
                                   amount = 1, evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        r = self.srequest(c, '/services/activity/resource/include',
                          {'psid' : psid,
                           'uuid' : uuid,
                           'activity' : activity,
                           'need' : enc.encode(need),
                           'amount' : amount},
                          status = evidence, print_result = print_error)

    def _include_personal_resource(self, psid, activity, uuid, amount,
                                   evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/services/participant/resource/use',
                          {'psid' : psid,
                           'activity' : activity,
                           'uuid' : uuid,
                           'amount' : amount},
                          status = evidence, print_result = print_error)

    def _list_activity_resources(self, psid = None, project = None, activity = None,
                                 evidence = 200, print_error = False):
        c = httplib.HTTPConnection(host, port)
        dec = json.JSONDecoder()
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid,
                           'project' : project,
                           'uuid' : activity},
                          status = evidence, print_result = print_error)
        if evidence == 200:
            return dec.decode(r)
        else:
            return r

    def _activity_participation(self, psid, uuid, action = 'include',
                                evidence = 201, print_error = False):
        c = httplib.HTTPConnection(host, port)
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid,
                       'uuid' : uuid,
                       'action' : action},
                      status = evidence, print_result = print_error)
        

class mytest(common_test):
    """
    """

    def test_create_project(self, ):
        """
        """
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        request(c, '/services/project/create',
                {'name' : u'Новый проект',
                 'descr' : 'blah blah, something here',
                 'begin_date' : '2012-03-20T20:40:22',
                 'sharing' : 'open',
                 'ruleset' : 'despot',
                 'user_name' : u'Вася',
                 'user_descr' : u'местный дурачек'})
        r1 = c.getresponse()
        self.assertEqual(r1.status, httplib.CREATED)
        self._delete_project(dec.decode(r1.read())['psid'])
        request(c, '/services/project/create',
                {'descr' : 'blah blah, something here',
                 'begin_date' : '2012-03-20T20:40:22',
                 'sharing' : 'open',
                 'ruleset' : 'despot',
                 'user_name' : u'Вася',
                 'user_id' : 'some_id',
                 'user_descr' : u'местный дурачек'})
        r2 = c.getresponse()
        self.assertEqual(r2.status, httplib.PRECONDITION_FAILED)
        request(c, '/services/project/create', {'name' : 'jsij',
                                       'descr' : 'blah blah, something here',
                                       'begin_date' : '2012-03-20T20:22', # wrong date
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_id' : 'some_id',
                                       'user_descr' : u'местный дурачек'})
        r3 = c.getresponse()
        self.assertEqual(r3.status, httplib.PRECONDITION_FAILED)


    def test_list_projects(self, ):
        """check list projects
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psids=[]
        puuids = []
        for x in range(0, 50):
            request(c, '/services/project/create', {'name' : u'test project {0}'.format(x),
                                                    'descr' : u'description blah blah',
                                                    'begin_date' : datetime.datetime(2012, 3, 13, 12, 12, x).isoformat(),
                                                    'sharing' : 'open',
                                                    'ruleset' : 'despot',
                                                    'user_name' : u'Spiderman'})
            r = c.getresponse()
            self.assertEqual(r.status, httplib.CREATED)
            d = dec.decode(r.read())
            psids.append(d['psid'])
            puuids.append(d['uuid'])
        # пробуем посмотреть все проекты
        request(c, '/services/project/list', {})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 50) # мы не знаем выполнился ли
# тест на создание проектов раньше

        # пробуем смотреть только определенные проекты
        puuid = random.choice(puuids)
        r = self.srequest(c, '/services/project/list',
                          {'uuid' : puuid}, httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d['projects']), 1)
        self.assertEqual(d['projects'][0]['uuid'], puuid)
        
        

        # пробуем посмотреть проекты по строке поиска
        request(c, '/services/project/list', {'search' : 'test project'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 50)
        self.assertEqual(resp['pages'], 50)
        for pr in resp['projects']:
            self.assertTrue(('test project' in pr['name']) or ('test project' in pr['descr']))

        # запрашиваем проекты по дате
        request(c, '/services/project/list', {'begin_date' : '2012-03-13T12:12:30'}) # пропускаем первые 30 по дате
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 20)
        for pr in resp['projects']:
            self.assertTrue(string2datetime(pr['begin_date']) >= datetime.datetime(2012, 3, 13, 12, 12, 30))

        # пробуем пролистать страницами по 5 проектов на страницу
        for pn in range(0, 11): # должно быть 10 страниц
            request(c, '/services/project/list', {'page_number' : pn,
                                         'projects_per_page' : 5})
            r = c.getresponse()
            self.assertEqual(r.status, httplib.OK)
            resp = dec.decode(r.read())
            self.assertEqual(resp['pages'], 10)
            if pn == 10:        # последняя страница пустая
                self.assertEqual(0, len(resp['projects']))
            else:
                self.assertTrue(len(resp['projects']) <= 5)

        # пробуем искать проекты которых нету
        request(c, '/services/project/list', {'search' : '11111111111111'}) # таких названий или описаний в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        self.assertEqual(0, len(dec.decode(r.read())['projects']))
        for psid in psids:
            self._delete_project(psid)

            
    def test_change_project_status(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/services/project/create', {'name' : 'something',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'user name'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        request(c, '/services/project/status/change', {'psid' : psid, # все нормально
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/status/change', {'psid' : psid,
                                              'status' : 'blah blah'}) # не верный статус
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED) # должны зафейлиться

        request(c, '/services/project/create', {'name' : 'ajsdfasd',
                                       'sharing' : 'open',
                                       'ruleset' : 'vote', # создаем не управляемый проект
                                       'user_name' : 'someuser'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        self._delete_project(psid)
        psid = dec.decode(r.read())['psid']

        request(c, '/services/project/status/change', {'psid' : psid, # пробуем этот проект изменить
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)
        request(c, '/services/project/status/change', {'psid' : 'aisjdf', # не верный psid
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)
        self._delete_project(psid)

    def test_create_project_parameter(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/services/project/create', {'name' : 'test project',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'name blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psid = resp['psid']

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(False),
                                                 'value' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 1',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 2',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        # c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
        #                                                            'name' : 'parameter test name 3',
        #                                                            'tp' : 'text',
        #                                                            'value' : 'sdf',
        #                                                            'enum' : False}))
        # r = c.getresponse()
        # self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 4',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 23,
                                                 'values' : enc.encode([{'values' : 23}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 5',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'avasd',
                                                 'values' : enc.encode([{'value' : 'avasd',
                                                                         'caption' : 'asidf'},
                                                                        {'value' : 'sijsji',
                                                                         'caption' : 234}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/parameter/create', {'psid' : 'sdf',
                                                 'name' : 'parameter test name 6',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name', # must fail - same name of parameter
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 7',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}]),
                                                 'value' : 'asdf'}) # value is not from given sequence
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 8',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}]),
                                                 'value' : 'fufuf',
                                                 'descr' : 'asdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        self._delete_project(psid)

    def test_create_project_parameter_from_default_route(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, "/services/parameters/list", {})
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        defparams = dec.decode(r.read()) # список default параметров
        request(c, '/services/project/create', {'name' : 'project blah blah',
                                       'descr' : 'this is project',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'kumare'})
        r = c.getresponse()
        self.assertEqual(httplib.CREATED, r.status)
        resp = dec.decode(r.read())
        psid = resp['psid']
        request(c, '/services/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        params = dec.decode(r.read()) # список параметров проекта
        for defpar in defparams:
            if defpar['name'] in [p['name'] for p in params]: # дефолт параметр уже есть в проекте (создан во время создания проекта)
                request(c, '/services/project/parameter/create/fromdefault', {'psid' : psid,
                                                                     'uuid' : defpar['uuid']})
                r = c.getresponse()
                self.assertEqual(httplib.PRECONDITION_FAILED, r.status)
            else:               # дефолт параметра нет в параметрах проекта
                request(c, '/services/project/parameter/create/fromdefault', {'psid' : psid,
                                                                     'uuid' : defpar['uuid']})
                r = c.getresponse()
                self.assertEqual(httplib.CREATED, r.status)
        # создали все параметры из дефолтных, теперь проверим что параметры проекта совпадают со списокм дефолтных параметров
        names = set([(p['name'], p['default']) for p in defparams]) # дефолт параметры в множество
        request(c, '/services/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        ppars = dec.decode(r.read())
        pnames = set([(p['name'], p['value']) for p in ppars]) # новые параметры проекта в множестве
        self.assertEqual(names, pnames)
        self._delete_project(psid)

    def test_list_and_create_project_parameters(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/services/project/create', {'name' : 'prj11',
                                       'descr' : 'asdf',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'user'})
        r = c.getresponse()
        self.assertEqual(httplib.CREATED, r.status)
        psid = dec.decode(r.read())['psid']
        request(c, '/services/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        pps = dec.decode(r.read())
        request(c, '/services/project/parameter/create', {'psid' : psid,
                                                 'name' : 'you parameter',
                                                 'descr' : 'test parameter',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(False),
                                                 'value' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        request(c, '/services/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        pps2 = dec.decode(r.read())
        self.assertEqual(len(pps)+1, len(pps2))
        for p in pps:
            self.assertIn(p, pps2)

        self._delete_project(psid)

    def test_change_project_parameter_route(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/services/project/create', {'name' : 'adsadsf',
                                                'sharing' : 'close',
                                                'ruleset' : 'despot',
                                                'user_name' : 'asdfadf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        request(c, '/services/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        params = dec.decode(r.read())

        for param in params:
            self.assertIn(param['enum'], [True, False])
            if param['enum']:
                posible = [a['value'] for a in param['values']]
                request(c, '/services/project/parameter/change', {'psid' : psid,
                                                                  'uuid' : param['uuid'],
                                                                  'value' : '111222333'}) # не верное значение
                r = c.getresponse()
                self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

                request(c, '/services/project/parameter/list', {'psid' : psid})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.OK)
                pps = dec.decode(r.read())
                vl = [a['value'] for a in pps if a['uuid'] == param['uuid']][0]
                self.assertNotEqual(vl, '111222333') # данные не поменялись

                request(c, '/services/project/parameter/change', {'psid' : psid,
                                                                  'uuid' : param['uuid'],
                                                                  'value' : posible[0]})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.CREATED)

                request(c, '/services/project/parameter/list', {'psid' : psid})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.OK)
                pps = dec.decode(r.read())
                vl = [a['value'] for a in pps if a['uuid'] == param['uuid']][0]
                self.assertEqual(vl, posible[0]) # значение сменилось
            else:
                request(c, '/services/project/parameter/change', {'psid' : psid,
                                                                  'uuid' : param['uuid'],
                                                                  'value' : 'asdjfasidfkaj'})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.CREATED)

                request(c, '/services/project/parameter/list', {'psid' : psid})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.OK)
                pps = dec.decode(r.read())
                vl = [a['value'] for a in pps if a['uuid'] == param['uuid']][0]
                self.assertEqual(vl, 'asdjfasidfkaj')
        self._delete_project(psid)

    def test_enter_project_open_route(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psds = []
        request(c, '/services/project/create', {'name' : 'blahblah',
                                                'sharing' : 'open',
                                                'ruleset' : 'despot',
                                                'user_name' : 'user'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psds.append(resp['psid'])

        request(c, '/services/project/status/change', {'psid' : resp['psid'],
                                                       'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/enter/open', {'uuid' : resp['uuid'],
                                                    'name' : 'blah blah'})
                                                    # 'user_id' : 'something'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        d = dec.decode(r.read())
        self.assertIn('psid', d)
        self.assertIn('token', d)

        request(c, '/services/project/enter/open', {'uuid' : resp['uuid'],
                                                    'name' : 'blah blah'}) # same name can not enter
                                                    # 'user_id' : 'sdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        # request(c, '/services/project/enter/open', {'uuid' : resp['uuid'],
        #                                             'name' : 'blahsdf blah',
        #                                             'user_id' : 'something'})
        # r = c.getresponse()
        # self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/status/change', {'psid' : resp['psid'],
                                                       'status' : 'contractor'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/enter/open', {'uuid' : resp['uuid'],
                                                    'name' : 'fjfj'})
                                                    # 'user_id' : 'jajaja'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/services/project/create', {'name' : 'pojer',
                                                'sharing' : 'close',
                                                'ruleset' : 'despot',
                                                'user_name' : 'sdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psds.append(resp['psid'])

        request(c, '/services/project/status/change', {'psid' : resp['psid'],
                                                       'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/services/project/enter/open', {'uuid' : resp['uuid'],
                                                    'name' : 'some'})
                                                    # 'user_id' : 'asdfasd'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED) # проект - закрытый

        for p in psds:
            self._delete_project(p)


    def test_list_projects2(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psid = []
        request(c, '/services/project/create', {'name' : 'somename',
                                                'sharing' : 'open',
                                                'ruleset' : 'despot',
                                                'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/services/project/create', {'name' : 'somename2',
                                                'sharing' : 'open',
                                                'ruleset' : 'despot',
                                                'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/services/project/create', {'name' : 'somename3',
                                                'sharing' : 'open',
                                                'ruleset' : 'despot',
                                                'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/services/project/create', {'name' : 'somename3',
                                                'sharing' : 'opened',
                                                'ruleset' : 'despot',
                                                'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)


        r = self.srequest(c, '/services/project/list', {}, httplib.OK)
        prs = dec.decode(r)['projects']
        self.assertEqual(set(['somename', 'somename2', 'somename3']),
                         set([a['name'] for a in prs]))
        for pr in psid:
            self._delete_project(pr)

    def test_invite_and_enter_participant(self, ):
        psids = []
        token, psid, puuid = self._auth_user_and_get_project()
        psids.append(psid)

        
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)

        # приглашаем участника в свой проект
        r = self.srequest(c, '/services/participant/invite', {'psid' : psid,
                                                              'name' : 'ololosh',
                                                              'comment' : 'This is the test',
                                                              'email' : 'ololosh@mail.ru'},
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], PROJECT_STATUS_MUST_BE_PLANNING)

        r = self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                                 'status' : 'planning'},
                          httplib.CREATED)

        r = self.srequest(c, '/services/participant/invite', {'psid' : psid,
                                                              'name' : 'ololosh',
                                                              'comment' : 'This is the test',
                                                              'email' : 'ololosh@mail.ru'},
                          httplib.CREATED)
        resp = dec.decode(r)
        self.assertIn('token', resp)
        token = resp['token']

        # проверяем что участник доступен
        r = self.srequest(c, '/services/participant/list', {'psid' : psid}, httplib.OK)
        prtsps = dec.decode(r)
        self.assertEqual(2, len(prtsps))
        notme = [a for a in prtsps if not a['me']][0] # должен быть тот самый участник
        for (a, b) in [('ololosh', notme['name']),
                       ('accepted', notme['status']),
                       (0, len(notme['votes']))]:
            self.assertEqual(a, b)

        # приглашенный участник входит на проект
        r = self.srequest(c, '/services/project/enter/invitation', {'uuid' : puuid,
                                                                    'token' : token},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid2 = resp['psid']

        # зашедший участник меняет сам себя
        self.srequest(c, '/services/participant/change', {'psid' : psid2,
                                                          'name' : 'vasek'},
                      httplib.CREATED)

        # а теперь тоже самое но с uuid
        r = self.srequest(c, '/services/participant/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)

        # участник с нашим именем имеет поле `me` == True
        self.assertEqual([True], [a['me'] for a in resp if a['name'] == 'vasek'])
        self.assertEqual([False], [a['me'] for a in resp if a['name'] != 'vasek'])

        self.assertIn('vasek', [a['name'] for a in resp])
        uuid2 = [a['uuid'] for a in resp if a['name'] == 'vasek'][0] #взяли свой
                                        #uuid
        usertoken2 = self._get_authenticated_user('vasek@mail.ru', 'pssword', 'vasek')
        r = self.srequest(c, '/services/participant/change', {'psid' : psid2,
                                                              'uuid' : uuid2,
                                                              'name' : 'vasek',
                                                              'user_id' : usertoken2},
                          httplib.CREATED)
        
        # зашедщий участник приглашает друга
        r = self.srequest(c, '/services/participant/invite', {'psid' : psid2,
                                                              'name' : 'second',
                                                              'descr' : 'just some stranger',
                                                              'email' : 'second@mail.ru'},
                                                     # 'user_id' : 'you you'},
                          status = httplib.CREATED)
        resp = dec.decode(r)
        token3 = resp['token']

        # зашедший участник правит дурга
        r = self.srequest(c, '/services/participant/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertIn('second', [a['name'] for a in resp])
        uuid3 = [a['uuid'] for a in resp if a['name'] == 'second'][0] #взяли uuid второго друга

        r = self.srequest(c, '/services/participant/change', {'psid' : psid2,
                                                              'uuid' : uuid3,
                                                              'name' : 'mister guy',
                                                              'descr' : 'the best fried of vasek'},
                          httplib.CREATED)

        # участник повторно добавляет того же друга и ничего не происходит
        r = self.srequest(c, '/services/participant/invite', {'psid' : psid2,
                                                              'name' : 'mister guy',
                                                              'email' : 'second@mail.ru'},
                          status = httplib.CREATED)

        # участник повторно добавляет того же друго но указывает не верные данные
        self.srequest(c, '/services/participant/invite', {'psid' : psid2,
                                                          'name' : 'mister guy',
                                                          'descr' : 'blah blah another description',
                                                          'email' : 'second@mail.ru'},
                      httplib.PRECONDITION_FAILED)

        # участни повторно дабавляет того же участника и указывает теже данные
        self.srequest(c, '/services/participant/invite', {'psid' : psid2,
                                                          'name' : 'mister guy',
                                                 # 'user_id' : 'you you',
                                                          'descr' : 'the best fried of vasek',
                                                          'email' : 'second@mail.ru'},
                      httplib.CREATED)


        # участник меняет друга так что он совпадает с существующим пользователем
        r = self.srequest(c, '/services/participant/change', {'psid' : psid2,
                                                              'uuid' : uuid3,
                                                              'name' : 'vasek'}, # это имя уже есть
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], PARTICIPANT_ALREADY_EXISTS)

        # инициатор согласует добавление второго друга
        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid,
                                                                'vote' : 'include',
                                                                'uuid' : uuid3},
                      httplib.CREATED)

        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid,
                                                                'vote' : 'include',
                                                                'uuid' : uuid3},
                      httplib.CREATED)

        # зашедщий друг пытается править друга и фейлится
        r = self.srequest(c, '/services/project/enter/invitation', {'uuid' : puuid,
                                                                    'token' : token3},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid3 = resp['psid']

        r = self.srequest(c, '/services/participant/change', {'psid' : psid3,
                                                              'uuid' : uuid2,
                                                              'name' : 'loh'},
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], ACCESS_DENIED)

        # каждый участник смотрит список участников
        lss = []
        for psd in [psid, psid3, psid3]:
            request(c, '/services/participant/list', {'psid' : psd})
            r = c.getresponse()
            self.assertEqual(r.status, httplib.OK)
            resp = dec.decode(r.read())
            lss.append(resp)

        sets = [set([(a['uuid'], a['name'], a['descr'], a['status']) for a in b]) for b in lss]
        for tails in sets[1:]:
            self.assertEqual(sets[0], tails)   # все списки одинаковые

        # первый друг удаляет второго друга
        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid2,
                                                                'uuid' : uuid3,
                                                                'vote' : 'exclude',
                                                                'comment' : 'dont like'},
                      httplib.CREATED)

        # инициатор это согласует
        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid,
                                                                'uuid' : uuid3,
                                                                'vote' : 'exclude',
                                                                'comment' : 'i dont like him too'},
                      httplib.CREATED)

        # просматривается список участников - активный должно быть два
        r = self.srequest(c, '/services/participant/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(2, len([a for a in resp if a['status'] == 'accepted']))
        self.assertEqual(1, len([a for a in resp if a['status'] == 'denied']))

        # второй друг пытается удалить первого, но он уже удален так что фейлится
        r = self.srequest(c, '/services/participant/vote/conform', {'psid' : psid3,
                                                                    'uuid' : uuid2,
                                                                    'vote' : 'exclude',
                                                                    'comment' : 'He deleted me !'},
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], ACCESS_DENIED)

        # инициатор удаляет первого друга
        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid,
                                                                'vote' : 'exclude',
                                                                'uuid' : uuid2},
                      httplib.CREATED)

        # инициатор смотрит список участников - он один
        r = self.srequest(c, '/services/participant/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(1, len([a for a in resp if a['status'] == 'accepted']))
        self.assertEqual(2, len([a for a in resp if a['status'] == 'denied']))

        # инициатор пытается добавить друга 1 еще раз и фейлится (повторно добавлять нельзя)
        self.srequest(c, '/services/participant/invite', {'psid' : psid,
                                                          'name' : 'vasek'},
                      httplib.PRECONDITION_FAILED)

        # 2 друг пытается повторно войти по приглашению и фейлится
        self.srequest(c, '/services/project/enter/invitation', {'uuid' : puuid,
                                                                'token' : token3},
                      httplib.PRECONDITION_FAILED)

        for p in psids:
            self._delete_project(p)

    def test_null_blank(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/services/project/create', {'name' : '  ',
                                                          'sharing' : 'open',
                                                          'ruleset' : 'despot',
                                                          'user_name' : 'asdf'},
                          httplib.PRECONDITION_FAILED)
        self.srequest(c, '/services/project/create', {'name' : 'asdf',
                                                      'sharing' : 'open',
                                                      'ruleset' : 'despot',
                                                      'user_name' : ''},
                      httplib.PRECONDITION_FAILED)

    def test_activities(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psids = []
        token, psid, puuid = self._auth_user_and_get_project()
        psids.append(psid)

        # создаем мероприятие
        r = self.srequest(c, '/services/activity/create', {'psid' : psid,
                                                  'name' : 'activ1',
                                                  'descr' : 'sdfafad',
                                                  'begin' : '2012-10-10T10:10:42',
                                                  'end' : '2020-10-10T10:10:44'},
                          httplib.CREATED)
        resp = dec.decode(r)
        auuid1 = resp['uuid']

        self.srequest(c, '/services/activity/create', {'psid' : psid,
                                              'name' : 'activ1',
                                              'begin' : '2012-10-10T10:10:42',
                                              'end' : '2020-10-10T10:10:44'},
                      httplib.PRECONDITION_FAILED)

        # публикуем мероприятие
        self.srequest(c, '/services/activity/public', {'psid' : psid,
                                              'uuid' : auuid1,
                                              'comment' : 'hoy!'},
                      httplib.CREATED)

        # просматриваем список мероприятий
        r = self.srequest(c, '/services/activity/list', {'psid' : psid},
                          httplib.OK)

        resp = dec.decode(r)
        self.assertEqual(1, len(resp))
        a = resp[0]
        self.assertEqual(a['uuid'], auuid1)
        self.assertEqual(a['name'], 'activ1')
        self.assertEqual(a['status'], 'accepted')
        self.assertEqual(a['votes'], [])

        # входим в мероприятие
        self.srequest(c, '/services/activity/participation', {'psid' : psid,
                                                              'action' : 'include',
                                                              'uuid' : auuid1},
                      httplib.CREATED)

        self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                             'status' : 'planning'},
                      httplib.CREATED)

        # приглашаем второго участника
        r = self.srequest(c, '/services/participant/invite', {'psid' : psid,
                                                              'name' : 'part2',
                                                              'email' : 'second@mail.ru',
                                                              'descr' : 'blah blah'},
                          httplib.CREATED)
        resp = dec.decode(r)
        token2 = resp['token']

        r = self.srequest(c, '/services/participant/list', {'psid' : psid}, httplib.OK)
        prts = dec.decode(r)
        self.assertEqual(2, len(prts))
        uuid1 = [a['uuid'] for a in prts if a['name'] == 'part2'][0] # получили ид пользователя

        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid,
                                                       'uuid' : uuid1,
                                                       'vote' : 'include'},
                      httplib.CREATED)

        # второй участник входит в проект
        r = self.srequest(c, '/services/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token2},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid2 = resp['psid']

        # второй участник входит в мероприятие
        r = self.srequest(c, '/services/activity/participation', {'psid' : psid2,
                                                         'action' : 'include',
                                                         'uuid' : auuid1},
                          httplib.CREATED)

        # просатриваем список участников мероприятий: смотрим чтобы было два
        # участника

        r = self.srequest(c, '/services/activity/participant/list', {'psid' : psid,
                                                            'uuid' : auuid1},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set([p['uuid'] for p in prts]), set(resp))

        # второй участник создает мероприятие
        self.srequest(c, '/services/activity/create', {'psid' : psid2,
                                              'name' : 'activ2',
                                              'begin' : '2020-10-10T20:20:20', # вторая дата позднее
                                              'end' : '2010-10-10T20:20:20'},
                      httplib.PRECONDITION_FAILED)

        r = self.srequest(c, '/services/activity/create', {'psid' : psid2,
                                                  'name' : 'activ2',
                                                  'end' : '2020-10-10T20:20:20',
                                                  'begin' : '2010-10-10T20:20:20'},
                            httplib.CREATED)
        auuid2 = dec.decode(r)['uuid']

        # просмотр списка мероприятий двумя участниками: один видит созданное
        # мероприятие второй - нет
        r = self.srequest(c, '/services/activity/list', {'psid' : psid},
                          httplib.OK)
        self.assertEqual(1, len(dec.decode(r)))

        r = self.srequest(c, '/services/activity/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['created', 'accepted']), set([a['status'] for a in resp]))

        # публикация мероприятия участником
        self.srequest(c, '/services/activity/public', {'psid' : psid2,
                                              'uuid' : auuid2,
                                              'comment' : 'you ! this is a comment'},
                      httplib.CREATED)

        # снова список мероприятий, теперь инициатор видит учреждение как
        # предложенное для использования в роекте
        r = self.srequest(c, '/services/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['accepted', 'voted']), set([a['status'] for a in resp]))

        # подтверждение публикации инициатором
        self.srequest(c, '/services/activity/public', {'psid' : psid,
                                              'uuid' : auuid2},
                      httplib.CREATED)

        # теперь мероприятие видно как accepted
        r = self.srequest(c, '/services/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['accepted']), set([a['status'] for a in resp]))

        # второй участник пытается удалить мероприятие и фейлится потому что
        # мероприятие уже согласовано
        self.srequest(c, '/services/activity/delete', {'psid' : psid2,
                                              'uuid' : auuid2},
                      httplib.PRECONDITION_FAILED)

        # теперь инициатор видит мероприятие как активное
        r = self.srequest(c, '/services/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(2, len(resp))
        self.assertEqual(set(['accepted']), set([a['status'] for a in resp]))

        # второй участник создает еще одно мероприятие
        r = self.srequest(c, '/services/activity/create', {'psid' : psid2,
                                                  'name' : 'activ3',
                                                  'begin' : '2010-10-10T10:10:10',
                                                  'end' : '2010-10-11T10:10:10'},
                          httplib.CREATED)
        auuid3 = dec.decode(r)['uuid']

        # удаляет мероприяте
        self.srequest(c, '/services/activity/delete', {'psid' : psid2,
                                              'uuid' : auuid3},
                      httplib.CREATED)

        # просматривает список - мероприятия нет
        r = self.srequest(c, '/services/activity/list', {'psid' : psid2},
                          httplib.OK)
        self.assertEqual(2, len(dec.decode(r)))

        # второй участник предлагает удалить второе мероприятие
        self.srequest(c, '/services/activity/deny', {'psid' : psid2,
                                            'uuid' : auuid2},
                      httplib.CREATED)

        # в списке мероприятий появляется предложение на удаление мероприятия
        r = self.srequest(c, '/services/activity/list', {'psid' : psid2},
                          httplib.OK)

        resp = dec.decode(r)
        x = [r for r in resp if len(r['votes']) > 0]
        self.assertEqual(1, len(x))
        a = x[0]

        vt = a['votes'][0]
        self.assertEqual('exclude', vt['vote'])

        # инициатор подтверждает действие
        self.srequest(c, '/services/activity/deny', {'psid' : psid,
                                            'uuid' : auuid2},
                      httplib.CREATED)

        # в списке мероприятий мероприяте меняет статус на "denied"
        r = self.srequest(c, '/services/activity/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual([], [a for a in resp if len(a['votes']) > 0])
        self.assertEqual(set(['accepted', 'denied']), set([a['status'] for a in resp]))
        for p in psids:
            self._delete_project(p)

    def test_activity_parameter(self, ):
        psids = []
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/services/project/create', {'name' : 'proj1',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'asdf'},
                          httplib.CREATED)

        psid = dec.decode(r)['psid']
        puuid = dec.decode(r)['uuid']
        psids.append(psid)

        self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/activity/create', {'psid' : psid,
                                                  'name' : 'newact',
                                                  'begin' : '2010-10-10T20:20:20',
                                                  'end' : '2010-10-11T20:20:20'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']
        self.srequest(c, '/services/activity/public', {'psid' : psid,
                                              'uuid' : auuid,
                                              'comment' : 'public'},
                      httplib.CREATED)

        # создаем параметр
        r = self.srequest(c, '/services/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par1',
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False)},
                          httplib.CREATED)
        p1 = dec.decode(r)['uuid']

        # фейлимся
        r = self.srequest(c, '/services/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par1', # создание параметра с тем же именем
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False)},
                          httplib.PRECONDITION_FAILED)

        # создаем еще один с ограниченным набором значений
        r = self.srequest(c, '/services/activity/parameter/create',
                          {'psid' : psid,
                           'uuid' : auuid,
                           'name' : 'par2',
                           'tp' : 'text',
                           'enum' : enc.encode(True),
                           'values' : enc.encode([{'value' : 'val1'},
                                                  {'value' : 'val2',
                                                   'caption' : 'val2'}])},
                          httplib.CREATED)
        p2 = dec.decode(r)['uuid']

        # фейлимся
        self.srequest(c, '/services/activity/parameter/create', {'psid' : psid,
                                                        'uuid' : auuid,
                                                        'name' : 'par3',
                                                        'tp' : 'text',
                                                        'enum': enc.encode(True)}, # не указаны перечисляемые значения
                      httplib.PRECONDITION_FAILED)

        # создаем третий параметр
        r = self.srequest(c, '/services/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par3',
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False),
                                                            'value' : 'this is the default value'},
                          httplib.CREATED)
        p3 = dec.decode(r)['uuid']

        # создаем параметр имя которого совпадает с именем типового параметра из фикстуры
        self.srequest(c, '/services/activity/parameter/create', {'psid' : psid,
                                                        'uuid' : auuid,
                                                        'name' : 'test asdf',
                                                        'tp' : 'text',
                                                        'enum' : enc.encode(False)},
                      httplib.CREATED)

        # просматриваем созданные параметры
        r = self.srequest(c, '/services/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)

        # просматриваем типовые параметры
        r = self.srequest(c, '/services/parameters/list', {}, httplib.OK)
        defprms = dec.decode(r)

        # создаем параметры из типовых и проверяем чтобы статус возврата был
        # фейловым на параметрах с тем же именем что уже есть
        for defprm in defprms:
            self.srequest(c, '/services/activity/parameter/create/fromdefault', {'psid' : psid,
                                                                        'uuid' : auuid,
                                                                        'default' : defprm['uuid']},
                          httplib.PRECONDITION_FAILED if (defprm['name'] in [a['name'] for a in prms]) else httplib.CREATED)

        # добавляем участника
        r = self.srequest(c, '/services/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'spiderman',
                                                     'user_id' : 'blah blah'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        # меняем первый параметр
        self.srequest(c, '/services/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p1,
                                                        'value' : 'newval'},
                      httplib.CREATED)

        # смотрим что значение поменялось в списке параметров
        r = self.srequest(c, '/services/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        val = [a['value'] for a in prms if a['uuid'] == p1][0]
        self.assertEqual(val, 'newval')

        # гость предлагает сменить значение первого параметра
        self.srequest(c, '/services/activity/parameter/change', {'psid' : psid2,
                                                        'uuid' : p1,
                                                        'value' : 'nextval',
                                                        'comment' : 'jff'},
                      httplib.CREATED)

        # проверяем что появилось предложение по этому параметру
        r = self.srequest(c, '/services/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        prm = [a for a in prms if a['uuid'] == p1][0]
        self.assertEqual(prm['value'], 'newval')
        self.assertEqual(1, len(prm['votes']))
        self.assertEqual('nextval', prm['votes'][0]['value'])

        # инициатор предлагает такое же значение и подтверждает
        self.srequest(c, '/services/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p1,
                                                        'value' : 'nextval',
                                                        'comment' : 'ok'},
                      httplib.CREATED)

        # проверяем что значение сменилось
        r = self.srequest(c, '/services/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        prm = [a for a in prms if a['uuid'] == p1][0]
        self.assertEqual([], prm['votes'])
        self.assertEqual('nextval', prm['value'])


        # Пробуем сменить значение параметра с ограниченным набором значений
        # на значение не из набора и фейлимся
        self.srequest(c, '/services/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p2,
                                                        'value' : '1111111'},
                      httplib.PRECONDITION_FAILED)

        for p in psids:
            self._delete_project(p)


    def test_self_deleting_test(self, ):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        r = self.srequest(c, '/services/project/create', {'name' : 'asdf',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'asdf'},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid = resp['psid']
        puuid = resp['uuid']

        self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'blalajs',
                                                     'user_id' : 'jsjsjfs'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']
        token = dec.decode(r)['token']

        self.srequest(c, '/services/participant/vote/conform', {'psid' : psid2,
                                                       'vote' : 'exclude'},
                      httplib.CREATED)

        self.srequest(c, '/services/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token},
                      httplib.PRECONDITION_FAILED)

        self._delete_project(psid)

    def test_resources(self, ):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        psids = []
        r = self.srequest(c, '/services/project/create', {'name' : 'wow super project',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'the god'},
                          httplib.CREATED)
        psid = dec.decode(r)['psid']
        psids.append(psid)
        puuid = dec.decode(r)['uuid']

        r = self.srequest(c, '/services/activity/create', {'psid' : psid,
                                                  'begin' : '2010-10-10',
                                                  'end' : '2010-10-10',
                                                  'name' : 'new activity'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']

        self.srequest(c, '/services/activity/public', {'psid' : psid,
                                              'uuid' : auuid},
                      httplib.CREATED)

        self.srequest(c, '/services/activity/participation', {'psid' : psid,
                                                     'action' : 'include',
                                                     'uuid' : auuid},
                      httplib.CREATED)

        # создаем личный ресурс
        self.srequest(c, '/services/resource/create', {'psid' : psid,
                                              'name' : 'kolbasa',
                                              'units' : u'kg',
                                              'use' : 'personal',
                                              'site' : 'internal'},
                      httplib.CREATED)

        # ресурс виден в общем списке (не по мероприятию)
        r = self.srequest(c, '/services/activity/resource/list', {'psid' : psid},

                          httplib.OK)
        rsrs = dec.decode(r)
        self.assertEqual(1, len(rsrs))
        personal = rsrs[0]
        for a, b in [('kolbasa', personal['name']),
                     (u'', personal.get('descr')),
                     (u'kg', personal['units']),
                     ('personal', personal['use']),
                     ('internal', personal['site']),
                     (False, personal['used']),
                     (0, len(personal['votes']))]:
            self.assertEqual(a, b)

        # добавляем ресурс на мероприятие

        r = self.srequest(c, '/services/activity/resource/include',
                          {'psid' : psid,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'need' : enc.encode(True),
                           'amount' : 100500},
                          httplib.CREATED)

        # проверяем что он добавлен
        r = self.srequest(c, '/services/activity/resource/list', {'psid' : psid,
                                                         'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, rs['amount']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # удаляем ресурс из мероприятия
        r = self.srequest(c, '/services/activity/resource/exclude',
                          {'psid' : psid,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'comment' : 'test'},
                          httplib.CREATED)

        # проверяем что он запрещен
        r = self.srequest(c, '/services/activity/resource/list', {'psid' : psid,
                                                         'uuid' : auuid},
                          httplib.OK)
        self.assertEqual(1, len(dec.decode(r)))
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        r = self.srequest(c, '/services/activity/resource/list', {'psid' : psid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # второй участник входит в проект
        self.srequest(c, '/services/project/status/change',
                      {'uuid' : puuid,
                       'status' : 'planning',
                       'psid' : psid},
                      httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open',
                          {'uuid' : puuid,
                           'name' : 'test user',
                           'user_id' : 'super user you you'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        # второй участник предлагает использовать ресурс повторно и фейлится ибо
        # нельзя вводить один и тот же ресурс повторно
        r = self.srequest(c, '/services/activity/resource/include',
                          {'psid' : psid2,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'need' : enc.encode(True),
                           'comment' : 'Here is comment'},
                          httplib.PRECONDITION_FAILED)

        # второй участник создает свой ресурс
        r = self.srequest(c, '/services/resource/create', {'psid' : psid2,
                                                  'name' : 'myaso',
                                                  'descr' : 'Myaso korovy',
                                                  'units' : 'kg',
                                                  'use' : 'personal',
                                                  'site' : 'external'},
                          httplib.CREATED)
        personal2 = dec.decode(r)['uuid']


        # второй участник предлагает ресурс на мероприятие и фелится потому что
        # еще не вошел на мероприятие
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid2,
                       'uuid' : personal2,
                       'activity' : auuid,
                       'comment' : 'Here is comment'},
                      httplib.PRECONDITION_FAILED)

        # второй входит на мероприятие
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid2,
                       'action' : 'include',
                       'uuid' : auuid,
                       'comment' : 'Oh i forgot'},
                      httplib.CREATED)

        # второй предлагает ресурс
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid2,
                       'uuid' : personal2,
                       'activity' : auuid,
                       'comment' : 'Here is comment'},
                      httplib.CREATED)

        # предложение видно
        r = self.srequest(c, '/services/activity/resource/list', {'psid' : psid2,
                                                         'uuid' : auuid},
                          httplib.OK)
        rs = [a for a in dec.decode(r) if a['uuid'] == personal2][0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, rs['amount']), # Для личного ресурса количество игнорируется при добавлении
                     (1, len(rs['votes'])),
                     ('include', rs['votes'][0]['vote']),
                     ('Here is comment', rs['votes'][0]['comment'])]:
            self.assertEqual(a, b)

        # инициатор подтверждает
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : personal2,
                       'activity' : auuid,
                       'need' : enc.encode(True),
                       'amount' : 9000},
                      httplib.CREATED)

        # проверяем что у ресурса пропали предложения
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        rs = [a for a in dec.decode(r) if a['uuid'] == personal2][0]
        for a, b in [(False, rs['used']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # второй участник использует ресурс как личный
        r = self.srequest(c, '/services/participant/resource/use',
                          {'psid' : psid2,
                           'uuid' : personal2,
                           'activity' : auuid,
                           'amount' : 10},
                          httplib.CREATED)

        # второй участник видит что ресурс используется
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        rs = [a for a in dec.decode(r) if a['uuid'] == personal2][0]
        for a, b in [(True, rs['used']),
                     (10, rs['amount'])]: # количество для личного ресурса при личном использовании
            self.assertEqual(a, b)

        # второй участник убирает ресурс из личного пользования
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : personal2,
                       'activity' : auuid,
                       'amount' : 0},
                      httplib.CREATED)

        # второй участник видит что он больше не использует этот ресурс
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        rs = [a for a in dec.decode(r) if a['uuid'] == personal2][0]
        for a, b in [(False, rs['used']),
                     (0, rs['amount'])]:
            self.assertEqual(a, b)

        # создаем общий ресурс
        self.srequest(c, '/services/resource/create',
                      {'psid' : psid,
                       'name' : 'vodka32',
                       'units' : u'liter',
                       'use' : 'common',
                       'site' : 'external'},
                      httplib.CREATED)

        # смотрим что такое есть
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        rsrs = dec.decode(r)
        self.assertEqual(3, len(rsrs))
        common = [a for a in rsrs if a['use'] == 'common'][0]
        for a, b in [('vodka32', common['name']),
                     (u'liter', common['units'])]:
            self.assertEqual(a, b)


        # добавляем его в мероприятие
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : common['uuid'],
                       'activity' : auuid,
                       'need' : enc.encode(True),
                       'amount' : 10,
                       'comment' : 'good vodka'},
                      httplib.CREATED)

        # видим что ресурс используется
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        rsrs = dec.decode(r)
        self.assertEqual(3, len(rsrs))
        rs = [a for a in rsrs if a['use'] == 'common'][0]
        for a, b in [(True, rs['used']),
                     (10, rs['amount'])]:
            self.assertEqual(a, b)


        # второй участник пытается использовать общий ресурс как личный и
        # фейлится
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : common['uuid'],
                       'activity' : auuid,
                       'amount' : 100},
                      httplib.PRECONDITION_FAILED)

        for p in psids:
            self._delete_project(p)

    def test_resource_parameters(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/services/project/create', {'name' : 'some proj',
                                                 'ruleset' : 'despot',
                                                 'sharing' : 'open',
                                                 'user_name' : 'main'},
                          httplib.CREATED)
        psid = dec.decode(r)['psid']
        psids = [psid]
        puuid = dec.decode(r)['uuid']

        self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/activity/create', {'psid' : psid,
                                                  'name' : 'activity1',
                                                  'begin' : '2010-10-10',
                                                  'end' : '2010-10-10'},
                          httplib.CREATED)

        auuid = dec.decode(r)['uuid']

        self.srequest(c, '/services/activity/public', {'psid' : psid,
                                              'uuid' : auuid},
                      httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'user1',
                                                     'descr' : 'Just some guy'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        self.srequest(c, '/services/activity/participation', {'psid' : psid2,
                                                     'action' : 'include',
                                                     'uuid' : auuid},
                      httplib.CREATED)

        self.srequest(c, '/services/activity/participation', {'psid' : psid,
                                                     'action' : 'include',
                                                     'uuid' : auuid},
                      httplib.CREATED)

        # Создаем общий ресурс
        r = self.srequest(c, '/services/resource/create', {'psid' : psid,
                                                  'name' : 'common',
                                                  'units' : 'kg',
                                                  'use' : 'common',
                                                  'site' : 'external'},
                          httplib.CREATED)
        d = dec.decode(r)
        common = d['uuid']

        # добавляем параметр ресурса и фейлимся - ресурс еще не в мероприятии
        self.srequest(c, '/services/activity/resource/parameter/create',
                      {'psid' : psid,
                       'activity' : auuid,
                       'uuid' : common,
                       'name' : 'param1',
                       'tp' : 'someparam',
                       'enum' : enc.encode(True),
                       'values' : enc.encode([{'value' : 'value1',
                                               'caption' : 'caption1'},
                                              {'value' : 'value2'}])},
                      httplib.PRECONDITION_FAILED)

        # добавляем ресурс в мероприятие
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'activity' : auuid,
                       'uuid' : common,
                       'need' : enc.encode(True),
                       'amount' : 10},
                      httplib.CREATED)

        # добавляем параметр ресурса
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : common,
                           'name' : 'param1',
                           'tp' : 'text',
                           'enum' : enc.encode(True),
                           'values' : enc.encode([{'value' : 'value1',
                                                   'caption' : 'caption1'},
                                                  {'value' : 'value2'}])},
                          httplib.CREATED)
        d = dec.decode(r)
        commp = d['uuid']       # ид параметра общего ресурса

        # просматриваем список параметров, смотрим что такой есть
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : common},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(1, len(d))
        p = d[0]
        for a, b in [(commp, p['uuid']),
                     ('param1', p['name']),
                     ('text', p['tp']),
                     (True, p['enum']),
                     (set(['value1', 'value2']), set([a['value'] for a in p['values']])),
                     (2, len(p['values']))]:

            self.assertEqual(a, b)

        # второй участник добавляет реусурсу еще параметр
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : common,
                           'name' : 'param2',
                           'tp' : 'text',
                           'enum' : enc.encode(False),
                           'value' : 'value'},
                          httplib.CREATED)
        d = dec.decode(r)
        commp2 = d['uuid']      # второй параметр общего ресурса

        # в списке параметров видно предложение
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : common},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(2, len(d))
        cp2 = [a for a in d if a['uuid'] == commp2][0]
        for a, b in [(1, len(cp2['votes'])),
                     ('value', cp2['votes'][0]['value'])]:
            self.assertEqual(a, b)

        # инициатор подтверждает
        self.srequest(c, '/services/activity/resource/parameter/change',
                      # для подтверждения меняем значение парметра на то же
                      # самое или ставим свое значение чтобы заменить
                      # предложенное значение своим
                      {'psid' :psid,
                       'uuid' : commp2,
                       'value' : 'value2',
                       'caption' : 'just caption',
                       'comment' : 'just comment'},
                      httplib.CREATED)

        # в списке видно два значения
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : common},
                          httplib.OK)
        d = dec.decode(r)
        p2 = [a for a in d if a['uuid'] == commp2][0]
        for a, b in [(set([commp, commp2]), set([a['uuid'] for a in d])),
                     (2, len(d)),
                     (0, len(p2['votes'])),
                     ('value2', p2['value']),
                     ('param2', p2['name'])]:
            self.assertEqual(a, b)

        # ======================================
        # второй добавляет личный ресурс
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid2,
                           'name' : 'resourc2',
                           'descr' : 'personal resource',
                           'units' : 'liter',
                           'use' : 'personal',
                           'site' : 'external'},
                          httplib.CREATED)
        personal = dec.decode(r)['uuid']

        # второй добавляет ресурс на мероприятие
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid2,
                       'uuid' : personal,
                       'activity' : auuid,
                       'comment' : 'this is the comment'},
                      httplib.CREATED)

        # инициатор подтверждает
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : personal,
                       'activity' : auuid})

        # второй добавляет параметр в ресурс и фейлится ибо еще не задействовал
        # личный ресурс
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : personal,
                           'name' : 'personal',
                           'tp' : 'float',
                           'enum' : enc.encode(False)},
                          httplib.PRECONDITION_FAILED)

        # второй задействует личный ресрус
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : personal,
                       'activity' : auuid,
                       'amount' : 10},
                      httplib.CREATED)

        # второй добавляет в личный ресурс параметр
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : personal,
                           'name' : 'personal',
                           'tp' : 'float',
                           'enum' : enc.encode(False)},
                          httplib.CREATED)

        persp = dec.decode(r)['uuid']

        # второй выставлет значение параметра для личного ресурса
        self.srequest(c, '/services/activity/resource/parameter/change',
                      {'psid' : psid2,
                       'uuid' : persp,
                       'value' : 100,
                       'caption' : 'just caption'},
                      httplib.CREATED)

        # просматривает значение параметра видит что оно изменилось
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : personal},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(1, len(d))
        pp = d[0]
        for a, b in [(persp, pp['uuid']),
                     ('personal', pp['name']),
                     ('float', pp['tp']),
                     (False, pp['enum']),
                     ([], pp['values']),
                     ('100', pp['value']),
                     ([], pp['votes']),
                     ('just caption', pp['caption'])]:
            self.assertEqual(a, b)

        # инициатор не видит даже параметра
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : personal},
                          httplib.OK)
        self.assertEqual(0, len(dec.decode(r)))
        # pp = dec.decode(r)[0]
        # for a, b in [(persp, pp['uuid']),
        #              ('personal', pp['name']),
        #              ('float', pp['tp']),
        #              (False, pp['enum']),
        #              ([], pp['values']),
        #              (None, pp['value']),
        #              ([], pp['votes']),
        #              ('just caption', pp['caption'])]:
        #     self.assertEqual(a, b)

        # инициатор добавляет ресурс как личный
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid,
                       'uuid' : personal,
                       'activity' : auuid,
                       'amount' : 200},
                      httplib.CREATED)

        # инициатор добавляет такой же параметр личного ресурса
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : personal,
                           'name' : 'personal',
                           'tp' : 'float',
                           'enum' : enc.encode(False)},
                          httplib.CREATED)
        persp2 = dec.decode(r)['uuid']


        # инициатор меняет значение этого ресурса
        self.srequest(c, '/services/activity/resource/parameter/change',
                      {'psid' : psid,
                       'uuid' : persp2,
                       'value' : 200,
                       'caption' : 'just caption',
                       'comment' : 'just comment'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : personal},
                          httplib.OK)
        pp = dec.decode(r)[0]
        for a, b in [(persp2, pp['uuid']),
                     ('personal', pp['name']),
                     ('float', pp['tp']),
                     (False, pp['enum']),
                     ([], pp['values']),
                     ('200', pp['value']),
                     ([], pp['votes']),
                     ('just caption', pp['caption'])]:
            self.assertEqual(a, b)

        # второй по прежнему видит старое значение
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : personal},
                          httplib.OK)
        pp = dec.decode(r)[0]
        for a, b in [(persp, pp['uuid']),
                     ('personal', pp['name']),
                     ('float', pp['tp']),
                     (False, pp['enum']),
                     ([], pp['values']),
                     ('100', pp['value']),
                     ([], pp['votes']),
                     ('just caption', pp['caption'])]:
            self.assertEqual(a, b)
        # ======================================
        # иницатор удаляет параметр личного ресурса
        # self.srequest(c, '/services/activity/resource/parameter/

        # в списке параметров это видно
        # второй удаляет параметр 1 общего ресурса
        # в списке видно предложение на удаление
        # инициатор подтверждает
        # в списке остается еще один параметр общего ресурса (второй)

        for p in psids:
            self._delete_project(p)

    def test_activity_resource_costs(self, ):
        """test rightness of calculations
        """
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        r = self.srequest(c, '/services/project/create', {'name' : 'someprojname',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'root'},
                          httplib.CREATED)
        d = dec.decode(r)
        psid = d['psid']
        psids = [psid]
        puuid = d['uuid']

        self.srequest(c, '/services/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/activity/create', {'psid' : psid,
                                                  'name' : 'activity1',
                                                  'begin' : '2010-10-10',
                                                  'end' : '2010-10-11'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']

        r = self.srequest(c, '/services/activity/public', {'psid' : psid,
                                                  'uuid' : auuid},
                          httplib.CREATED)

        r = self.srequest(c, '/services/activity/participation', {'psid' : psid,
                                                         'action' : 'include',
                                                         'uuid' : auuid},
                          httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'user1',
                                                     'user_id' : 'user_id_1'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        self.srequest(c, '/services/activity/participation', {'psid' : psid2,
                                                     'action' : 'include',
                                                     'uuid' : auuid},
                      httplib.CREATED)

        ## теперь оба участника вошли на проект и в мероприятие

        # создаем общий ресурс на мероприятии в количестве 100 едениц
        r = self.srequest(c, '/services/resource/create', {'psid' : psid,
                                                  'name' : 'res1',
                                                  'units' : 'kg',
                                                  'use' : 'common',
                                                  'site' : 'external'},
                          httplib.CREATED)
        res1 = dec.decode(r)['uuid']

        self.srequest(c, '/services/activity/resource/include', {'psid' : psid,
                                                        'uuid' : res1,
                                                        'activity' : auuid,
                                                        'need' : enc.encode(False),
                                                        'amount' : 100},
                      httplib.CREATED)

        # подключается поставщик и предлагает за ресурс цену 10 денег за еденицу
        # ресурса

        self.srequest(c, '/services/contractor/create', {'user' : 'contr1',
                                                'name' : 'contr1'},
                          httplib.CREATED)
        cont1 = 'contr1'

        r = self.srequest(c, '/services/project/list', {'search' : 'someprojname'},
                          httplib.OK)
        d = dec.decode(r)
        pjs = d['projects']
        self.assertEqual(1, len(pjs))
        self.assertEqual(puuid, pjs[0]['uuid']) # то что мы получили в списке -
                                                # тот проект который только что создали
        r = self.srequest(c, '/services/contractor/project/resource/list',
                          {'uuid' : puuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(1, len(d))
        self.assertEqual(res1, d[0]['uuid'])
        rr = d[0]
        for a, b in [(100, 'amount'),
                     (100, 'free_amount'),
                     ('res1', 'name'),
                     ('kg', 'units'),
                     ('external', 'site'),
                     ('common', 'use')]:
            self.assertEqual(a, rr[b])

        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : cont1,
                       'uuid' : res1,
                       'cost' : 10},
                      httplib.CREATED)

        # в списке ресурсов проекта видно предложение поставщика
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(1, len(d))
        rr = d[0]
        for a, b in [('uuid', res1),
                     ('name', 'res1'),
                     ('units', 'kg'),
                     ('used', True),
                     ('amount', 100),
                     ('cost', 0),
                     ]:
            self.assertEqual(rr[a], b)
        cc = rr['contractors']
        self.assertEqual(1, len(cc))
        c1 = cc[0]
        for a, b in [('name', 'contr1'),
                     ('user', 'contr1'),
                     ('cost', 10),
                     ('amount', 0),
                     ('offer_amount', None),
                     ]:
            self.assertEqual(c1[a], b)
        self.assertEqual(0, len(c1['votes']))

        # подключается второй поставщик
        self.srequest(c, '/services/contractor/create',
                      {'user' : 'contr2',
                       'name' : 'contr2',
                       'contacts' : enc.encode([{'type' : 'email',
                                                 'value' : 'mail@mail.ru'}])},
                      httplib.CREATED)

        # в списке поставщиков видно 2 поставщика
        r = self.srequest(c, '/services/contractor/list', {}, httplib.OK)
        d = dec.decode(r)
        self.assertEqual(2, len(d))
        self.assertEqual(set(['contr1', 'contr2']), set([a['user'] for a in d]))
        self.assertEqual(set(['contr1', 'contr2']), set([a['name'] for a in d]))
        snd = [a for a in d if a['user'] == 'contr2'][0]
        self.assertEqual([{'type' : 'email',
                           'value' : 'mail@mail.ru'}], snd['contacts'])

        # предлагает цену 9
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr2',
                       'uuid' : res1,
                       'cost' : 9},
                      httplib.CREATED)

        # в списке ресурсов участники проекта наблюдают два предложения по
        # ресурсу
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(1, len(d))
        ccs = d[0]['contractors']
        self.assertEqual(set(['contr1', 'contr2']), set([a['name'] for a in ccs]))
        self.assertEqual(set(['contr1', 'contr2']), set([a['user'] for a in ccs]))
        cr1 = [a for a in ccs if a['user'] == 'contr1'][0]
        cr2 = [a for a in ccs if a['user'] == 'contr2'][0]
        self.assertEqual(cr1['cost'], 10)
        self.assertEqual(cr2['cost'], 9)

        # участники проекта создают второй ресурс в количестве 200
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid,
                           'name' : 'res2',
                           'units' : 'kg',
                           'site' : 'external',
                           'use' : 'common'},
                          httplib.CREATED)
        d = dec.decode(r)
        res2 = d['uuid']

        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : res2,
                       'activity' : auuid,
                       'need' : enc.encode(False),
                       'amount' : 200},
                      httplib.CREATED)

        # первый поставщик предлагает цену 20 за второй ресурс
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr1',
                       'uuid' : res2,
                       'cost' : 20},
                      httplib.CREATED)

        # второй поставщик предлагает цену 15 за второй ресурс в количестве 100
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr2',
                       'uuid' : res2,
                       'cost' : 15,
                       'amount' : 100},
                      httplib.CREATED)

        # в списке ресурсов видно, что по второму ресурсу 2 предложения
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        rs2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(2, len(rs2['contractors']))
        cr1 = [a for a in rs2['contractors'] if a['user'] == 'contr1'][0]
        cr2 = [a for a in rs2['contractors'] if a['user'] == 'contr2'][0]
        for a, b in [('name', 'contr1'),
                     ('cost', 20),
                     ('amount', 0),
                     ('offer_amount', None)
                     ]:
            self.assertEqual(cr1[a], b)
        for a, b in [('name', 'contr2'),
                     ('cost', 15),
                     ('amount', 0),
                     ('offer_amount', 100)
                     ]:
            self.assertEqual(cr2[a], b)

        # первый поставщик снимает свое предложение во второму ресурсв
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr1',
                       'uuid' : res2,
                       'cost' : 0,
                       'amount' : 0},
                      httplib.CREATED)

        # в списке ресурсов видно что только один поставщик предлагает второй ресурс
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        rs2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(1, len(rs2['contractors']))

        # проект переводится в режим contractor
        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'status' : 'contractor'},
                      httplib.CREATED)

        # второй участник предлагает использовать первого поставщика для первого
        # ресурса в количестве 50
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid2,
                       'resource' : res1,
                       'contractor' : 'contr1',
                       'amount' : 50},
                      httplib.CREATED)

        # в списке ресурсов в первом ресурсе в первом поставщике видно
        # предложение на использование от второго пользователя
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid}, httplib.OK)
        d = dec.decode(r)
        rs1 = [a for a in d if a['uuid'] == res1][0]
        cr1 = [a for a in rs1['contractors'] if a['user'] == 'contr1'][0]
        self.assertEqual(1, len(cr1['votes']))
        self.assertEqual(cr1['votes'][0]['amount'], 50)

        # инициатор подтверждает использование первого поставщика для 50 едениц
        # первого ресурса
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid,
                       'resource' : res1,
                       'contractor' : 'contr1',
                       'amount' : 50},
                      httplib.CREATED)

        # в списке ресурсов видно, что первый ресурс поставляется первым
        # поставщиком в количестве 50 по цене 10, цена за ресурс составляет 500
        # r = self.srequest(c, '/services/activity/resource/list',
        #                   {'psid' : psid}, httplib.OK)
        # d = dec.decode(r)
        # rs1 = [a for a in d if a['uuid'] == res1][0]



        # второй поставщик в списке ресурсов видит что проекту требуется уже только 50
        # едениц первого ресурса
        r = self.srequest(c, '/services/contractor/project/resource/list',
                          {'uuid' : puuid},
                          httplib.OK)
        d = dec.decode(r)
        rs1 = [a for a in d if a['uuid'] == res1][0]
        self.assertEqual(rs1['amount'], 100)
        self.assertEqual(rs1['free_amount'], 50)

        # инициатор использует второго поставщика для остатка первого ресурса
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid,
                       'resource' : res1,
                       'contractor' : 'contr2'},
                      httplib.CREATED)

        # второй участник предлагает второго поставщика для второго
        # ресурса
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid2,
                       'resource' : res2,
                       'contractor' : 'contr2'},
                      httplib.CREATED)

        # в списке поставщиков второго ресурса видно 1 предложение по
        # второму поставщику в количестве 100 (минимум между доступным от поставщика и
        # необходимым на проекте)
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        rs2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(1, len(rs2['contractors']))
        c1 = rs2['contractors'][0]
        self.assertEqual('contr2', c1['user'])
        self.assertEqual(1, len(c1['votes']))
        self.assertEqual(100, c1['votes'][0]['amount'])

        # инициатор подтверждает
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid,
                       'resource' : res2,
                       'contractor' : 'contr2'},
                      httplib.CREATED)

        # в списке ресурсов видно что второй ресурс доставляется вторым
        # поставщиком в количестве 100 из 200 необходимых на проекте, видно, что
        # цена за первый ресурс = 50 * 10 + 50 * 9 = 950 денег, за второй ресурс
        # 100 * 15 = 1500 денег.
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        rs1 = [a for a in d if a['uuid'] == res1][0]
        rs2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(rs1['cost'], 950)
        self.assertEqual(rs2['cost'], 1500)
        self.assertEqual(rs2['amount'], 200)
        cr1 = rs2['contractors'][0]
        self.assertEqual(cr1['amount'], 100)
        self.assertEqual(cr1['offer_amount'], 100)
        self.assertEqual(cr1['votes'], [])

        # перевод проекта в режим planning
        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'status' : 'planning'},
                      httplib.CREATED)


        # добавляется второе мероприятие и в него входят оба участника
        r = self.srequest(c, '/services/activity/create',
                          {'psid' : psid,
                           'name' : 'activity2',
                           'begin' : '2010-10-10',
                           'end' : '2010-10-10'},
                          httplib.CREATED)
        auuid2 = dec.decode(r)['uuid']
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid,
                       'uuid' : auuid2},
                      httplib.CREATED)
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid,
                       'action' : 'include',
                       'uuid' : auuid2},
                      httplib.CREATED)
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid2,
                       'action' : 'include',
                       'uuid' : auuid2},
                      httplib.CREATED)

        # во втором мероприятии создается личный ресурс 3
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid,
                           'name' : 'res3',
                           'units' : 'kg',
                           'use' : 'personal',
                           'site' : 'external'},
                          httplib.CREATED)
        res3 = dec.decode(r)['uuid']
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : res3,
                       'activity' : auuid2,
                       'need' : enc.encode(True)},
                      httplib.CREATED)
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : res3,
                       'activity' : auuid,
                       'need' : enc.encode(False)},
                      httplib.CREATED)

        # первый участник использует 10 едениц 3 ресурса на втором мероприятии
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid,
                       'uuid' : res3,
                       'activity' : auuid2,
                       'amount' : 10},
                      httplib.CREATED)

        # второй участник использует 10 едениц 3 ресурса на втором мероприятии
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : res3,
                       'activity' : auuid2,
                       'amount' : 10},
                      httplib.CREATED)

        # первый участник использует 15 едениц 3 ресурса на первом мероприятии
        self.srequest(c, '/services/participant/resource/use',
                      {'psid' : psid,
                       'uuid' : res3,
                       'activity' : auuid,
                       'amount' : 15},
                      httplib.CREATED)

        # первый поставщик предлагает цену 5 денег за еденицу 3 ресурса но в
        # количестве только 20 из необходимых участникам 35
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr1',
                       'uuid' : res3,
                       'cost' : 5,
                       'amount' : 20},
                      httplib.CREATED)

        # второй поставщик предлгаает 3 ресурс в неограниченном количестве, но
        # цена 20 денег за еденицу несурса
        self.srequest(c, '/services/contractor/resource/offer',
                      {'user' : 'contr2',
                       'uuid' : res3,
                       'cost' : 20},
                      httplib.CREATED)

        # инициаотр переводит проект в режим contractor
        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'status' : 'contractor'},
                      httplib.CREATED)

        # инициатор решает заказать 3 ресурс у первого поставщика полностью а
        # остальное докупить у второго поставщика
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid,
                       'resource' : res3,
                       'contractor' : 'contr1'},
                      httplib.CREATED)
        self.srequest(c, '/services/resource/contractor/use',
                      {'psid' : psid,
                       'resource' : res3,
                       'contractor' : 'contr2'},
                      httplib.CREATED)

        ## ============== просмотр старистики ================

        # r = self.srequest(c, '/services/project/report',
        #                   {'psid' : psid},
        #                   httplib.OK)
        # d = dec.decode(r)
        # for a, b in [('uuid', puuid),
        #              ('name', 'someprojname'),
        #              ('sharing', 'open'),
        #              ('ruleset', 'despot'),
        #              ('cost', 2850),
        #              ]:
        #     self.assertEqual(d[a], b)
        # resources = d['resources']
        # self.assertEqual(len(resources), 3)
        # resource1 = [a for a in resources if a['uuid'] == res1][0]
        # resource2 = [a for a in resources if a['uuid'] == res2][0]
        # resource3 = [a for a in resources if a['uuid'] == res3][0]
        # for a, b in [('amount', 100),
        #              ('available', 100),
        #              ('cost', 950),
        #              ('name', 'res1'),
        #              ('units', 'kg'),
        #              ('use', 'common'),
        #              ('site', 'external'),
        #              ]:
        #     self.assertEqual(resource1[a], b)
        # for a, b in [('amount', 200),
        #              ('available', 100),
        #              ('cost', 1500),
        #              ('name', 'res2'),
        #              ('units', 'kg'),
        #              ('use', 'common'),
        #              ('site', 'external'),
        #              ]:
        #     self.assertEqual(resource2[a], b)
        # for a, b in [('amount', 35),
        #              ('available', 35),
        #              ('cost', 400),
        #              ('name', 'res3'),
        #              ('units', 'kg'),
        #              ('use', 'personal'),
        #              ('site', 'external'),
        #              ]:
        #     self.assertEqual(resource3[a], b)


        r = self.srequest(c, '/services/participant/report',
                          {'psid' : psid},
                          httplib.OK)
        rdd = dec.decode(r)
        d = rdd['participants']
        self.assertEqual(len([a for a in d if a['is_initiator']]), 1)
        self.assertEqual(len(d), 2)
        partic1 = [a for a in d if a['name'] == 'root'][0]
        partic2 = [a for a in d if a['name'] == 'user1'][0]
        self.assertEqual(True, partic1['is_initiator'])
        for partic in [partic1, partic2]:
            partre1 = [a for a in partic['resources'] if a['uuid'] == res1][0]
            for a, b in [('amount', 50),
                         ('available', 50),
                         ('cost', 475), # 950 / 2
                         ('name', 'res1'),
                         ('min_cost', None),
                         ('max_cost', None),
                         ('mean_cost', None),
                         ('units', 'kg'),
                         ('use', 'common'),
                         ('site', 'external')
                         ]:
                self.assertEqual(partre1[a], b)
            partre2 = [a for a in partic['resources'] if a ['uuid'] == res2][0]
            for a, b in [('amount', 100),
                         ('available', 50),
                         ('cost', 750), # 1500 / 2
                         ('name', 'res2'),
                         ('min_cost', None),
                         ('max_cost', None),
                         ('mean_cost', None),
                         ('units', 'kg'),
                         ('use', 'common'),
                         ('site', 'external')
                         ]:
                self.assertEqual(partre2[a], b)

        p1re3 = [a for a in partic1['resources'] if a['uuid'] == res3][0]
        for a, b in [('amount', 25),
                     ('available', 25),
                     ('cost', 400. / 35. * 25.),
                     ('name', 'res3'),
                     ('min_cost', None),
                     ('max_cost', None),
                     ('mean_cost', None),
                     ('units', 'kg'),
                     ('use', 'personal'),
                     ('site', 'external')
                     ]:
            self.assertEqual(p1re3[a], b)
        p2re3 = [a for a in partic2['resources'] if a['uuid'] == res3][0]
        for a, b in [('amount', 10),
                     ('available', 10),
                     ('cost', 400. / 35. * 10.),
                     ('name', 'res3'),
                     ('min_cost', None),
                     ('max_cost', None),
                     ('mean_cost', None),
                     ('units', 'kg'),
                     ('use', 'personal'),
                     ('site', 'external'),
                     ]:
            self.assertEqual(p2re3[a], b)
        self.assertEqual(partic1['cost'], (400. / 35. * 25.) + 475 + 750)
        self.assertEqual(partic2['cost'], (400. / 35. * 10.) + 475 + 750)
        self.assertEqual(rdd['cost'], 400 + 1500 + 950)
        self.assertEqual(rdd['min_cost'], None)
        self.assertEqual(rdd['max_cost'], None)
        self.assertEqual(rdd['mean_cost'], None)


        for p in psids:
            self._delete_project(p)

    def test_created_activity(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/services/project/create',
                          {'name' : 'proj1',
                           'sharing' : 'open',
                           'ruleset' : 'despot',
                           'user_name' : 'root'},
                          httplib.CREATED)
        puuid = dec.decode(r)['uuid']
        psid = dec.decode(r)['psid']
        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open',
                          {'uuid' : puuid,
                           'name' : 'user1'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        # второй участник создает новое мероприятие
        r = self.srequest(c, '/services/activity/create',
                          {'psid' : psid2,
                           'name' : 'activ1',
                           'begin' : '2010-10-10',
                           'end' : '2012-10-10'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']

        # второй участник входит в еще только созданное мероприятие
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid2,
                       'action' : 'include',
                       'uuid' : auuid},
                      httplib.CREATED)

        # первый участник пытается войти в мероприятие и фейлится потому что не
        # он создтатель этого мероприятия
        self.srequest(c, '/services/activity/participation',
                      {'psid' : psid,
                       'action' : 'include',
                       'uuid' : auuid},
                      httplib.PRECONDITION_FAILED)

        # второй участник создает на проекте ресурс
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid2,
                           'name' : 'res1',
                           'units' : 'kg',
                           'use' : 'common',
                           'site' : 'external'},
                          httplib.CREATED)
        res1 = dec.decode(r)['uuid']

        # второй участник добавляет ресурс на мероприятие
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid2,
                       'uuid' : res1,
                       'activity' : auuid,
                       'need' : enc.encode(True),
                       'amount' : 20},
                      httplib.CREATED)

        # второй участник смотрит список мероприятий и видит что созданное
        # мероприятие содержит один неактивный ресурс и предложение по ресурсу
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid2},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]['participant'], True)

        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 1)
        for a, b in [('uuid', res1),
                     ('status', 'voted'),
                     ('used', False),
                     ('amount', 20),
                     ]:
            self.assertEqual(d[0][a], b)

        self.assertEqual(len(d[0]['votes']), 1)
        self.assertEqual(d[0]['votes'][0]['vote'], 'include')

        # второй участник добавляет личный ресурс
        r = self.srequest(c, '/services/resource/create',
                          {'psid' : psid2,
                           'name' : 'res2',
                           'units' : 'kg',
                           'use' : 'personal',
                           'site' : 'external'},
                          httplib.CREATED)
        res2 = dec.decode(r)['uuid']
        self.srequest(c, '/services/activity/resource/include',
                      {'psid' : psid2,
                       'uuid' : res2,
                       'activity' : auuid},
                      httplib.CREATED)

        # второй участник видит два ресурса, по второму только предложение
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 2)
        resource1 = [a for a in d if a['uuid'] == res1][0]
        self.assertEqual(len(resource1['votes']), 1)
        self.assertEqual(resource1['status'], 'voted')
        self.assertEqual(resource1['votes'][0]['vote'], 'include')
        resource2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(len(resource1['votes']), 1)
        self.assertEqual(resource1['status'], 'voted')
        self.assertEqual(resource1['votes'][0]['vote'], 'include')

        # второй участник добавляет параметр личного ресурса
        # r = self.srequest(c, '/services/activity/resource/parameter/create',
        #               {'psid' : psid2,
        #                'activity' : auuid,
        #                'uuid' : res2,
        #                'name' : 'p1',
        #                'tp' : 'text',
        #                'enum' : enc.encode(False),
        #                'value' : 'value1'},
        #               httplib.CREATED, True)
        # param3 = dec.decode(r)['uuid']

        # второй участник видит что параметр личного ресурса присутствует с
        # пустым значением и одним предолжением
        # r = self.srequest(c, '/services/activity/resource/parameter/list',
        #                   {'psid' : psid2,
        #                    'uuid' : res2,
        #                    'activity' : auuid},
        #                   httplib.OK)
        # d = dec.decode(r)
        # for a, b in [('name', 'p1'),
        #              ('value', None),
        #              ('enum', False),
        #              ('tp', 'text'),
        #              ]:
        #     self.assertEqual(d[0][a], b)
        # self.assertEqual(len(d[0]['votes']), 1)
        # self.assertEqual(d[0]['votes'][0]['value'], 'value1')

        # второй участник создает параметр ресурса
        r = self.srequest(c, '/services/activity/resource/parameter/create',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : res1,
                           'name' : 'p1',
                           'tp' : 'text',
                           'enum' : enc.encode(False),
                           'value' : 'value1'},
                          httplib.CREATED)
        param1 = dec.decode(r)['uuid']

        # второй участник в списке параметров ресурсов видит предложение по
        # этому параметру
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid2,
                           'uuid' : res1,
                           'activity' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        for a, b in [('name', 'p1'),
                     ('value', None),
                     ('enum', False),
                     ('tp', 'text'),
                     ]:
            self.assertEqual(d[0][a], b)
        self.assertEqual(len(d[0]['votes']), 1)
        self.assertEqual(d[0]['votes'][0]['value'], 'value1')

        # второй участник создает типовой параметр ресурса
        r = self.srequest(c, '/services/parameters/list',
                          {},
                          httplib.OK)
        def1 = dec.decode(r)[0]['uuid']

        r = self.srequest(c, '/services/activity/resource/parameter/create/fromdefault',
                          {'psid' : psid2,
                           'activity' : auuid,
                           'uuid' : res1,
                           'default' : def1},
                          httplib.CREATED)
        param2 = dec.decode(r)['uuid']

        # второй участник видит что есть два параметра ресурса по обоим только
        # предложения, значение пустое
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid2,
                           'uuid' : res1,
                           'activity' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 2)
        for res in d:
            self.assertEqual(res['value'], None)
            self.assertEqual(len(res['votes']), 1)

        # второй участник создает параметр мероприятия
        r = self.srequest(c, '/services/activity/parameter/create',
                          {'psid' : psid2,
                           'uuid' : auuid,
                           'name' : 'param1',
                           'tp' : 'text',
                           'enum' : enc.encode(False),
                           'value' : 'value1'},
                          httplib.CREATED)

        # второй участник в списке параметров мероприятия видит предложение по
        # этому параметру
        r = self.srequest(c, '/services/activity/parameter/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]['value'], None)
        self.assertEqual(len(d[0]['votes']), 1)
        self.assertEqual(d[0]['votes'][0]['value'], 'value1')

                           #  FIXME: доделать такое же для default параметра
        # второй участник публикует мероприятие
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid2,
                       'uuid' : auuid},
                      httplib.CREATED)

        # первый участник видит опубликованное мероприятие
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]['status'], 'voted')
        self.assertEqual(d[0]['uuid'], auuid)

        # первый участник видит предложение по обоим ресурсам
        r = self.srequest(c, '/services/activity/resource/list',
                             {'psid' : psid,
                              'uuid' : auuid},
                             httplib.OK)
        d = dec.decode(r)
        resource1 = [a for a in d if a['uuid'] == res1][0]
        self.assertEqual(len(resource1['votes']), 1)
        self.assertEqual(resource1['status'], 'voted')
        self.assertEqual(resource1['votes'][0]['vote'], 'include')
        resource2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(len(resource1['votes']), 1)
        self.assertEqual(resource1['status'], 'voted')
        self.assertEqual(resource1['votes'][0]['vote'], 'include')

        # первый участник видит два предложения параметрам ресурса
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'uuid' : res1,
                           'activity' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 2)
        for res in d:
            self.assertEqual(res['value'], None)
            self.assertEqual(len(res['votes']), 1)

        # первый участник видит предложение по параметру второго ресурса
        # r = self.srequest(c, '/services/activity/resource/parameter/list',
        #                   {'psid' : psid,
        #                    'uuid' : res2,
        #                    'activity' : auuid},
        #                   httplib.OK)
        # d = dec.decode(r)
        # for a, b in [('name', 'p1'),
        #              ('value', None),
        #              ('enum', False),
        #              ('tp', 'text'),
        #              ]:
        #     self.assertEqual(d[0][a], b)
        # self.assertEqual(len(d[0]['votes']), 1)
        # self.assertEqual(d[0]['votes'][0]['value'], 'value1')

        # первый участник видит предложение по параметру мероприятия
        r = self.srequest(c, '/services/activity/parameter/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]['value'], None)
        self.assertEqual(len(d[0]['votes']), 1)
        self.assertEqual(d[0]['votes'][0]['value'], 'value1')

        # первый участник согласует мероприятие
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid,
                       'uuid' : auuid},
                      httplib.CREATED)

        # все видят созданное мероприятие
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid},
                          httplib.OK)
        activ = dec.decode(r)[0]
        self.assertEqual(activ['status'], 'accepted')
        self.assertEqual(len(activ['votes']), 0)

        # все видят в нем активный параметр
        r = self.srequest(c, '/services/activity/parameter/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d[0]['votes']), 0)
        self.assertEqual(d[0]['value'], 'value1')

        # все видят в нем два активных ресурса
        r = self.srequest(c, '/services/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        d = dec.decode(r)
        resource1 = [a for a in d if a['uuid'] == res1][0]
        self.assertEqual(len(resource1['votes']), 0)
        self.assertEqual(resource1['used'], True)
        self.assertEqual(resource1['amount'], 20)
        self.assertEqual(resource1['status'], 'accepted')
        resource2 = [a for a in d if a['uuid'] == res2][0]
        self.assertEqual(len(resource2['votes']), 0)
        self.assertEqual(resource2['used'], False)
        self.assertEqual(resource2['amount'], 0)
        self.assertEqual(resource2['status'], 'accepted')

        # все видят у ресурса два активнх параметра
        r = self.srequest(c, '/services/activity/resource/parameter/list',
                          {'psid' : psid,
                           'activity' : auuid,
                           'uuid' : res1},
                          httplib.OK)
        d = dec.decode(r)
        self.assertEqual(len(d), 2)
        for respar in d:
            self.assertNotEqual(respar['value'], None)
            self.assertEqual(len(respar['votes']), 0)

        # все видят у второго ресурса один активный параметр
        # r = self.srequest(c, '/services/activity/resource/parameter/list',
        #                   {'psid' : psid,
        #                    'activity' : auuid,
        #                    'uuid' : res2},
        #                   httplib.OK)
        # d = dec.decode(r)
        # self.assertEqual(len(d), 1)
        # for respar in d:
        #     self.assertEqual(respar['value'], 'value1')
        #     self.assertEqual(len(respar['votes']), 0)

        self._delete_project(psid)

    def test_public_as_include(self, ):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        r = self.srequest(c, '/services/project/create',
                          {'name':  'proj1',
                           'sharing' : 'open',
                           'ruleset' : 'despot',
                           'user_name' : 'root'},
                          httplib.CREATED)
        psid = dec.decode(r)['psid']
        puuid = dec.decode(r)['uuid']

        self.srequest(c, '/services/project/status/change',
                      {'psid' : psid,
                       'uuid' : puuid,
                       'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/services/project/enter/open',
                          {'uuid' : puuid,
                           'name' : 'user1',
                           'user_id' : 'user1'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        r = self.srequest(c, '/services/activity/create',
                          {'psid' : psid2,
                           'name' : 'activ1',
                           'begin' : '2010-10-10',
                           'end' : '2010-10-10'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid2,
                       'uuid' : auuid},
                      httplib.CREATED)
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid,
                       'uuid' : auuid},
                      httplib.CREATED)
        self.srequest(c, '/services/activity/deny',
                      {'psid' : psid2,
                       'uuid' : auuid},
                      httplib.CREATED)
        r = self.srequest(c, '/services/project/enter/open',
                          {'uuid' : puuid,
                           'name' : 'user2',
                           'user_id' : 'user2'},
                          httplib.CREATED)
        psid3 = dec.decode(r)['psid']
        self.srequest(c, '/services/activity/public', # голосуем за добавление мероприятия
                      {'psid' : psid3,
                       'uuid' : auuid},
                      httplib.CREATED)
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)[0]
        self.assertEqual(d['status'], 'accepted')
        self.assertEqual(len(d['votes']), 2)
        self.assertEqual(set(['include', 'exclude']), set([a['vote'] for a in d['votes']]))
        self.srequest(c, '/services/activity/public',
                      {'psid' : psid,
                       'uuid' : auuid},
                      httplib.CREATED)
        r = self.srequest(c, '/services/activity/list',
                          {'psid' : psid},
                          httplib.OK)
        d = dec.decode(r)[0]
        self.assertEqual(d['status'], 'accepted')
        self.assertEqual(len(d['votes']), 0)

        self._delete_project(psid)


    def test_authentication(self, ):
        psid, puuid = self._create_project()
        self._set_project_status(psid, 'planning')
        self._user_check('somebody@mail.ru',
                         evidence = 404)
        self._user_check('sdfasd@sdfasd',
                         evidence = 412)
        ret = self._create_user_account('somebody@mail.ru',
                                        'password',
                                        'name')
        self.assertEqual(ret['email'], 'somebody@mail.ru')
        self.assertEqual(ret['name'], 'name')
        self.assertEqual(ret['descr'], '')
        self._create_user_account('somebody@mail.ru',
                                  'password',
                                  'name',
                                  evidence = 409)
        ret = self._ask_user_confirmation('somebody@mail.ru')
        confirm = ret['confirmation']

        self._authenticate_user('somebody@mail.ru',
                                'password',
                                evidence = httplib.PRECONDITION_FAILED)

        self._confirm_account('somebody@mail.ru',
                              'asdf',
                              confirm,
                              evidence = httplib.PRECONDITION_FAILED)
        self._confirm_account('somebody@mail.ru',
                              'password',
                              '1234',
                              evidence = httplib.PRECONDITION_FAILED)
        self._confirm_account('somebody@mail.ru',
                              'password',
                              confirm)
        self._confirm_account('somebody@mail.ru',
                              'password',
                              confirm,
                              evidence = httplib.PRECONDITION_FAILED)

        self._ask_user_confirmation('somebody@mail.ru',
                                    evidence = 409)

        ret = self._authenticate_user('somebody@mail.ru',
                                      'password')
        for a, b in [('email', 'somebody@mail.ru'),
                     ('name', 'name'),
                     ('descr', '')]:
            self.assertEqual(ret[a], b)
        self.assertIn('token', ret)

        self._delete_project(psid)

    def test_logout(self, ):
        """Login logout test"""
        self._token_check('000000000', 409)
        self._logout('000000000', evidence = 409)
        token = self._get_authenticated_user('asdf34@asdf.ru', '123', '123')
        self._token_check(token, 200)
        self._logout(token, evidence = 201)
        self._token_check(token, 409)

    def test_open_project_list_activities(self):
        token = self._get_authenticated_user('asdf@asdf.ru', '1234', '1234')
        psid, puuid = self._create_project()
        auuid = self._create_activity(psid)
        self._public_activity(psid, auuid)
        self._list_activities(evidence = 412)
        acts = self._list_activities(uuid = puuid)
        acts2 = self._list_activities(psid = psid)
        self.assertEqual(len(acts), 1)
        self.assertEqual(len(acts2), 1)
        self.assertEqual(acts[0], acts2[0])
        self.assertEqual(acts[0]['uuid'], auuid)
        self._delete_project(psid)
        
    def test_enter_exit_project(self):
        token, psid, uuid = self._auth_user_and_get_project()
        self._change_project_status(psid, 'planning')
        psid2, token2 = self._enter_open_project(uuid, 'name1')
        self._check_project_participation(token, uuid, evidence = 200)
        self._check_project_participation(token2, uuid, evidence = 200)
        prjs, pages = self._list_projects()
        self.assertEqual(len(prjs), 1)
        self._exit_project(token2, uuid)
        self._check_project_participation(token2, uuid, evidence = 409) # больше не участник
        self._exit_project(token, uuid) # вышел последний участник - проект
# уничтожается
        self._check_project_participation(token, uuid, evidence = 409)
        prjs, pages = self._list_projects()
        self.assertEqual(len(prjs), 0)

    def test_list_participants_open_project(self):
        token, psid, puuid = self._auth_user_and_get_project()
        self._change_project_status(psid, 'planning')
        psid2, token2 = self._enter_open_project(puuid, 'name1')
        prts = self._list_participants(psid = psid)
        prts2 = self._list_participants(psid = psid, uuid = puuid)
        prts3 = self._list_participants(uuid = puuid)
        self.assertEqual(prts, prts2)
        self.assertEqual(set([a['uuid'] for a in prts]), set([a['uuid'] for a in prts3]))
        self._delete_project(psid)

    def test_list_activity_resources_open_project(self):
        token, psid, puuid = self._auth_user_and_get_project()
        self._change_project_status(psid, 'planning')
        auuid = self._create_activity(psid)
        self._public_activity(psid, auuid)
        self._activity_participation(psid, auuid)
        res1 = self._create_project_resource(psid)
        res2 = self._create_project_resource(psid, name = 'res2')
        self._include_activity_resource(psid, auuid, res1)
        l1 = self._list_activity_resources(psid)
        l2 = self._list_activity_resources(project = puuid)
        self._list_activity_resources(evidence = 412)
        self.assertEqual(l1, l2)
        l3 = self._list_activity_resources(psid, activity = auuid)
        l4 = self._list_activity_resources(project = puuid, activity = auuid)
        self.assertEqual(l3, l4)

        self._delete_project(psid)

        token2, psid2, puuid2 = self._auth_user_and_get_project(sharing = 'close')
        self._change_project_status(psid2, 'planning')
        auuid2 = self._create_activity(psid2)
        self._public_activity(psid2, auuid2)
        self._activity_participation(psid2, auuid2)
        res3 = self._create_project_resource(psid2)
        res4 = self._create_project_resource(psid2, name = 'asdf')
        self._include_activity_resource(psid2, auuid2, res3)
        self._list_activity_resources(project = puuid2, activity = auuid2, evidence = 412)
        self._list_activity_resources(project = puuid2, evidence = 412)

        self._delete_project(psid2)
        
        
        

if __name__ == '__main__':
    main()
