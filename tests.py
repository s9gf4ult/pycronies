#!/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main
import httplib, urllib
import json
from services.statuses import *
import datetime

host = '127.0.0.1'
port = 8000

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

class mytest(TestCase):
    """
    """
    def srequest(self, conn, route, data, status=None, print_result=False):
        dec = json.JSONDecoder()
        request(conn, route, data)
        r = conn.getresponse()
        ret = r.read()
        if print_result:
            try:
                print('>>>>>>>>> response to {0}:\n{1}'.format(route, dec.decode(ret)))
            except:
                print('>>>>>>>>> failed to parse response to {0}:\n{1}'.format(route, ret))
        if status != None:
            self.assertEqual(r.status, status)
        return ret

    def _delete_project(self, psid):
        """
        Arguments:
        - `psid`:
        """
        c = httplib.HTTPConnection(host, port)
        request(c, '/project/delete', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)

    def test_create_project(self, ):
        """
        """
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        request(c, '/project/create', {'name' : u'Новый проект',
                                       'descr' : 'blah blah, something here',
                                       'begin_date' : '2012-03-20T20:40:22',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : u'Вася',
                                       'user_id' : 'some_id',
                                       'user_descr' : u'местный дурачек'})
        r1 = c.getresponse()
        self.assertEqual(r1.status, httplib.CREATED)
        self._delete_project(dec.decode(r1.read())['psid'])
        request(c, '/project/create', {'descr' : 'blah blah, something here',
                                       'begin_date' : '2012-03-20T20:40:22',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : u'Вася',
                                       'user_id' : 'some_id',
                                       'user_descr' : u'местный дурачек'})
        r2 = c.getresponse()
        self.assertEqual(r2.status, httplib.PRECONDITION_FAILED)
        request(c, '/project/create', {'name' : 'jsij',
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
        for x in range(0, 50):
            request(c, '/project/create', {'name' : u'test project {0}'.format(x),
                                           'descr' : u'description blah blah',
                                           'begin_date' : datetime.datetime(2012, 3, 13, 12, 12, x).isoformat(),
                                           'sharing' : 'open',
                                           'ruleset' : 'despot',
                                           'user_name' : u'Spiderman'})
            r = c.getresponse()
            self.assertEqual(r.status, httplib.CREATED)
            psids.append(dec.decode(r.read())['psid'])
        # пробуем посмотреть все проекты
        request(c, '/project/list', {})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 50) # мы не знаем выполнился ли тест на создание проектов раньше

        # пробуем посмотреть проекты по строке поиска
        request(c, '/project/list', {'search' : 'test project'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 50)
        self.assertEqual(resp['pages'], 50)
        for pr in resp['projects']:
            self.assertTrue(('test project' in pr['name']) or ('test project' in pr['descr']))

        # запрашиваем проекты по дате
        request(c, '/project/list', {'begin_date' : '2012-03-13T12:12:30'}) # пропускаем первые 30 по дате
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(len(resp['projects']), 20)
        for pr in resp['projects']:
            self.assertTrue(string2datetime(pr['begin_date']) >= datetime.datetime(2012, 3, 13, 12, 12, 30))

        # пробуем пролистать страницами по 5 проектов на страницу
        for pn in range(0, 11): # должно быть 10 страниц
            request(c, '/project/list', {'page_number' : pn,
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
        request(c, '/project/list', {'search' : '11111111111111'}) # таких названий или описаний в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        self.assertEqual(0, len(dec.decode(r.read())['projects']))
        for psid in psids:
            self._delete_project(psid)

    def test_list_user_projects_route(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/project/create', {'name' : 'test',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'mega_user',
                                       'user_id' : 'test_id'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']
        request(c, '/project/list/userid', {'user_id' : 'test_id'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(1, len(resp))
        self.assertEqual(resp[0]['name'], 'test')
        self.assertEqual(resp[0]['initiator'], True)
        self.assertEqual(resp[0]['status'], 'opened')

        r = self.srequest(c, '/project/list/userid', {'user_id' : '11111111111'}, httplib.OK) # такого ид в базе нет
        self.assertEqual(0, len(dec.decode(r)))
        
        self._delete_project(psid)

    def test_change_project_status(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/project/create', {'name' : 'something',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'user name'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        request(c, '/project/status/change', {'psid' : psid, # все нормально
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/status/change', {'psid' : psid,
                                              'status' : 'blah blah'}) # не верный статус
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED) # должны зафейлиться

        request(c, '/project/create', {'name' : 'ajsdfasd',
                                       'sharing' : 'open',
                                       'ruleset' : 'vote', # создаем не управляемый проект
                                       'user_name' : 'someuser'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        self._delete_project(psid)
        psid = dec.decode(r.read())['psid']

        request(c, '/project/status/change', {'psid' : psid, # пробуем этот проект изменить
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)
        request(c, '/project/status/change', {'psid' : 'aisjdf', # не верный psid
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)
        self._delete_project(psid)

    def test_create_project_parameter(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        request(c, '/project/create', {'name' : 'test project',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'name blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psid = resp['psid']

        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(False),
                                                 'value' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 1',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/parameter/create', {'psid' : psid,
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

        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 4',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 23,
                                                 'values' : enc.encode([{'values' : 23}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/parameter/create', {'psid' : psid,
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

        request(c, '/project/parameter/create', {'psid' : 'sdf',
                                                 'name' : 'parameter test name 6',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)

        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name', # must fail - same name of parameter
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'value' : 'fufuf',
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}])})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'parameter test name 7',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(True),
                                                 'values' : enc.encode([{'value' : 'you you you',
                                                                         'caption' : 'blah blah'},
                                                                        {'value' : 'fufuf'}]),
                                                 'value' : 'asdf'}) # value is not from given sequence
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/parameter/create', {'psid' : psid,
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
        request(c, "/parameters/list", {})
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        defparams = dec.decode(r.read()) # список default параметров
        request(c, '/project/create', {'name' : 'project blah blah',
                                       'descr' : 'this is project',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'kumare'})
        r = c.getresponse()
        self.assertEqual(httplib.CREATED, r.status)
        resp = dec.decode(r.read())
        psid = resp['psid']
        request(c, '/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        params = dec.decode(r.read()) # список параметров проекта
        for defpar in defparams:
            if defpar['name'] in [p['name'] for p in params]: # дефолт параметр уже есть в проекте (создан во время создания проекта)
                request(c, '/project/parameter/create/fromdefault', {'psid' : psid,
                                                                     'uuid' : defpar['uuid']})
                r = c.getresponse()
                self.assertEqual(httplib.PRECONDITION_FAILED, r.status)
            else:               # дефолт параметра нет в параметрах проекта
                request(c, '/project/parameter/create/fromdefault', {'psid' : psid,
                                                                     'uuid' : defpar['uuid']})
                r = c.getresponse()
                self.assertEqual(httplib.CREATED, r.status)
        # создали все параметры из дефолтных, теперь проверим что параметры проекта совпадают со списокм дефолтных параметров
        names = set([(p['name'], p['default']) for p in defparams]) # дефолт параметры в множество
        request(c, '/project/parameter/list', {'psid' : psid})
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
        request(c, '/project/create', {'name' : 'prj11',
                                       'descr' : 'asdf',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'user'})
        r = c.getresponse()
        self.assertEqual(httplib.CREATED, r.status)
        psid = dec.decode(r.read())['psid']
        request(c, '/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        pps = dec.decode(r.read())
        request(c, '/project/parameter/create', {'psid' : psid,
                                                 'name' : 'you parameter',
                                                 'descr' : 'test parameter',
                                                 'tp' : 'text',
                                                 'enum' : enc.encode(False),
                                                 'value' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        request(c, '/project/parameter/list', {'psid' : psid})
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
        request(c, '/project/create', {'name' : 'adsadsf',
                                       'sharing' : 'close',
                                       'ruleset' : 'despot',
                                       'user_name' : 'asdfadf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        request(c, '/project/parameter/list', {'psid' : psid})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        params = dec.decode(r.read())

        for param in params:
            self.assertIn(param['enum'], [True, False])
            if param['enum']:
                posible = [a['value'] for a in param['values']]
                request(c, '/project/parameter/change', {'psid' : psid,
                                                        'uuid' : param['uuid'],
                                                        'value' : '111222333'}) # не верное значение
                r = c.getresponse()
                self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

                request(c, '/project/parameter/list', {'psid' : psid})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.OK)
                pps = dec.decode(r.read())
                vl = [a['value'] for a in pps if a['uuid'] == param['uuid']][0]
                self.assertNotEqual(vl, '111222333') # данные не поменялись

                request(c, '/project/parameter/change', {'psid' : psid,
                                                         'uuid' : param['uuid'],
                                                         'value' : posible[0]})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.CREATED)

                request(c, '/project/parameter/list', {'psid' : psid})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.OK)
                pps = dec.decode(r.read())
                vl = [a['value'] for a in pps if a['uuid'] == param['uuid']][0]
                self.assertEqual(vl, posible[0]) # значение сменилось
            else:
                request(c, '/project/parameter/change', {'psid' : psid,
                                                         'uuid' : param['uuid'],
                                                         'value' : 'asdjfasidfkaj'})
                r = c.getresponse()
                self.assertEqual(r.status, httplib.CREATED)

                request(c, '/project/parameter/list', {'psid' : psid})
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
        request(c, '/project/create', {'name' : 'blahblah',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'user'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psds.append(resp['psid'])

        request(c, '/project/status/change', {'psid' : resp['psid'],
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/enter/open', {'uuid' : resp['uuid'],
                                           'name' : 'blah blah',
                                           'user_id' : 'something'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        d = dec.decode(r.read())
        self.assertIn('psid', d)
        self.assertIn('token', d)

        request(c, '/project/enter/open', {'uuid' : resp['uuid'],
                                           'name' : 'blah blah', # same name can not enter
                                           'user_id' : 'sdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/enter/open', {'uuid' : resp['uuid'],
                                           'name' : 'blahsdf blah',
                                           'user_id' : 'something'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/status/change', {'psid' : resp['psid'],
                                              'status' : 'contractor'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/enter/open', {'uuid' : resp['uuid'],
                                           'name' : 'fjfj',
                                           'user_id' : 'jajaja'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/create', {'name' : 'pojer',
                                       'sharing' : 'close',
                                       'ruleset' : 'despot',
                                       'user_name' : 'sdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psds.append(resp['psid'])

        request(c, '/project/status/change', {'psid' : resp['psid'],
                                              'status' : 'planning'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/enter/open', {'uuid' : resp['uuid'],
                                           'name' : 'some',
                                           'user_id' : 'asdfasd'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        for p in psds:
            self._delete_project(p)


    def test_list_projects2(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psid = []
        request(c, '/project/create', {'name' : 'somename',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/project/create', {'name' : 'somename2',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/project/create', {'name' : 'somename3',
                                       'sharing' : 'open',
                                       'ruleset' : 'despot',
                                       'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid.append(dec.decode(r.read())['psid'])

        request(c, '/project/create', {'name' : 'somename3',
                                       'sharing' : 'opened',
                                       'ruleset' : 'despot',
                                       'user_name' : 'asdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)


        r = self.srequest(c, '/project/list', {}, httplib.OK)
        prs = dec.decode(r)['projects']
        self.assertEqual(set(['somename', 'somename2', 'somename3']),
                         set([a['name'] for a in prs]))
        for pr in psid:
            self._delete_project(pr)

    def test_invite_and_enter_participant(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psids = []
        request(c, '/project/create', {'name' : 'project1',
                                       'sharing' : 'invitation',
                                       'ruleset' : 'despot',
                                       'user_name' : 'blah blah',
                                       'user_id' : 'blah blah'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psid = resp['psid']
        puuid = resp['uuid']
        psids.append(psid)


        # приглашаем участника в свой проект
        r = self.srequest(c, '/participant/invite', {'psid' : psid,
                                                     'name' : 'ololosh',
                                                     'comment' : 'This is the test'},
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], PROJECT_STATUS_MUST_BE_PLANNING)

        r = self.srequest(c, '/project/status/change', {'psid' : psid,
                                                        'status' : 'planning'},
                          httplib.CREATED)

        r = self.srequest(c, '/participant/invite', {'psid' : psid,
                                                     'name' : 'ololosh',
                                                     'comment' : 'This is the test'},
                          httplib.CREATED)
        resp = dec.decode(r)
        self.assertIn('token', resp)
        token = resp['token']
        # проверяем что участник приглашен
        
        r = self.srequest(c, '/participant/list', {'psid' : psid}, httplib.OK)
        prtsps = dec.decode(r)
        self.assertEqual(2, len(prtsps))
        notme = [a for a in prtsps if not a['me']][0] # должен быть тот самый участник
        for (a, b) in [('ololosh', notme['name']),
                       ('voted', notme['status']),
                       (1, len(notme['votes'])),
                       ('include', notme['votes'][0]['vote']),
                       ('This is the test', notme['votes'][0]['comment'])]:
            self.assertEqual(a, b)

        # подтверждаем приглашение
        r = self.srequest(c, '/participant/list', {'psid' : psid}, httplib.OK)
        pts = dec.decode(r)
        uuid2 = [a['uuid'] for a in pts if a['name'] == 'ololosh'][0]

        self.srequest(c, '/participant/vote/conform', {'psid' : psid,
                                                       'uuid' : uuid2,
                                                       'vote' : 'include'},
                      httplib.CREATED)

        # проверяем что участник доступен
        r = self.srequest(c, '/participant/list', {'psid' : psid}, httplib.OK)
        prtsps = dec.decode(r)
        self.assertEqual(2, len(prtsps))
        notme = [a for a in prtsps if not a['me']][0] # должен быть тот самый участник
        for (a, b) in [('ololosh', notme['name']),
                       ('accepted', notme['status']),
                       (0, len(notme['votes']))]:
            self.assertEqual(a, b)

        # приглашенный участник входит на проект
        r = self.srequest(c, '/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid2 = resp['psid']

        # зашедший участник меняет сам себя
        self.srequest(c, '/participant/change', {'psid' : psid2,
                                                 'name' : 'vasek',
                                                 'user_id' : 'barlam barlam'},
                      httplib.CREATED)

        # а теперь тоже самое но с uuid
        r = self.srequest(c, '/participant/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)

        # участник с нашим именем имеет поле `me` == True
        self.assertEqual(set([True]), set([a['me'] for a in resp if a['name'] == 'vasek']))
        self.assertEqual(set([False]), set([a['me'] for a in resp if a['name'] != 'vasek']))
        
        self.assertIn('vasek', [a['name'] for a in resp])
        uuid2 = [a['uuid'] for a in resp if a['name'] == 'vasek'][0] #взяли свой uuid
        r = self.srequest(c, '/participant/change', {'psid' : psid2,
                                                     'uuid' : uuid2,
                                                     'name' : 'vasek',
                                                     'user_id' : 'barlam barlam'},
                          httplib.CREATED)

        # зашедщий участник приглашает друга
        r = self.srequest(c, '/participant/invite', {'psid' : psid2,
                                                     'name' : 'second',
                                                     'descr' : 'just some stranger',
                                                     'user_id' : 'you you'},
                          httplib.CREATED)
        resp = dec.decode(r)
        token3 = resp['token']

        # зашедший участник правит дурга
        r = self.srequest(c, '/participant/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertIn('second', [a['name'] for a in resp])
        uuid3 = [a['uuid'] for a in resp if a['name'] == 'second'][0] #взяли uuid второго друга

        r = self.srequest(c, '/participant/change', {'psid' : psid2,
                                                     'uuid' : uuid3,
                                                     'name' : 'mister guy',
                                                     'descr' : 'the best fried of vasek'},
                          httplib.CREATED)

        # участник повторно добавляет того же друга и ничего не происходит
        r = self.srequest(c, '/participant/invite', {'psid' : psid2,
                                                     'name' : 'mister guy'},
                          httplib.CREATED)

        # участник повторно добавляет того же друго но указывает не верные данные
        self.srequest(c, '/participant/invite', {'psid' : psid2,
                                                 'name' : 'mister guy',
                                                 'descr' : 'blah blah another description'},
                      httplib.PRECONDITION_FAILED)

        # участни повторно дабавляет того же участника и указывает теже данные
        self.srequest(c, '/participant/invite', {'psid' : psid2,
                                                 'name' : 'mister guy',
                                                 'user_id' : 'you you',
                                                 'descr' : 'the best fried of vasek'},
                      httplib.CREATED)


        # участник меняет друга так что он совпадает с существующим пользователем
        r = self.srequest(c, '/participant/change', {'psid' : psid2,
                                                     'uuid' : uuid3,
                                                     'name' : 'vasek'}, # это имя уже есть
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], PARTICIPANT_ALREADY_EXISTS)

        # инициатор согласует добавление второго друга
        self.srequest(c, '/participant/vote/conform', {'psid' : psid,
                                                             'vote' : 'include',
                                                             'uuid' : uuid3},
                      httplib.CREATED)

        self.srequest(c, '/participant/vote/conform', {'psid' : psid,
                                                             'vote' : 'include',
                                                             'uuid' : uuid3},
                      httplib.CREATED)
        
        # зашедщий друг пытается править друга и фейлится
        r = self.srequest(c, '/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token3},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid3 = resp['psid']

        r = self.srequest(c, '/participant/change', {'psid' : psid3,
                                                     'uuid' : uuid2,
                                                     'name' : 'loh'}, httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], ACCESS_DENIED)

        # каждый участник смотрит список участников
        lss = []
        for psd in [psid, psid3, psid3]:
            request(c, '/participant/list', {'psid' : psd})
            r = c.getresponse()
            self.assertEqual(r.status, httplib.OK)
            resp = dec.decode(r.read())
            lss.append(resp)

        sets = [set([(a['uuid'], a['name'], a['descr'], a['status']) for a in b]) for b in lss]
        for tails in sets[1:]:
            self.assertEqual(sets[0], tails)   # все списки одинаковые

        # первый друг удаляет второго друга
        self.srequest(c, '/participant/exclude', {'psid' : psid2,
                                                  'uuid' : uuid3,
                                                  'comment' : 'dont like'},
                      httplib.CREATED)

        # инициатор это согласует
        self.srequest(c, '/participant/exclude', {'psid' : psid,
                                                  'uuid' : uuid3,
                                                  'comment' : 'i dont like him too'},
                      httplib.CREATED)

        # просматривается список участников - активный должно быть два
        r = self.srequest(c, '/participant/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(2, len([a for a in resp if a['status'] == 'accepted']))
        self.assertEqual(1, len([a for a in resp if a['status'] == 'denied']))

        # второй друг пытается удалить первого, но он уже удален так что фейлится
        r = self.srequest(c, '/participant/exclude', {'psid' : psid3,
                                                      'uuid' : uuid2,
                                                      'comment' : 'He deleted me !'},
                          httplib.PRECONDITION_FAILED)
        resp = dec.decode(r)
        self.assertEqual(resp['code'], ACCESS_DENIED)

        # инициатор удаляет первого друга
        self.srequest(c, '/participant/exclude', {'psid' : psid,
                                                  'uuid' : uuid2},
                      httplib.CREATED)

        # инициатор смотрит список участников - он один
        r = self.srequest(c, '/participant/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(1, len([a for a in resp if a['status'] == 'accepted']))
        self.assertEqual(2, len([a for a in resp if a['status'] == 'denied']))

        # инициатор пытается добавить друга 1 еще раз и фейлится (повторно добавлять нельзя)
        self.srequest(c, '/participant/invite', {'psid' : psid,
                                                 'name' : 'vasek'},
                      httplib.PRECONDITION_FAILED)

        # 2 друг пытается повторно войти по приглашению и фейлится
        self.srequest(c, '/project/enter/invitation', {'uuid' : puuid,
                                                       'token' : token3},
                      httplib.PRECONDITION_FAILED)

        for p in psids:
            self._delete_project(p)

    def test_null_blank(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        r = self.srequest(c, '/project/create', {'name' : '  ',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'asdf'},
                          httplib.PRECONDITION_FAILED)
        self.srequest(c, '/project/create', {'name' : 'asdf',
                                             'sharing' : 'open',
                                             'ruleset' : 'despot',
                                             'user_name' : ''},
                      httplib.PRECONDITION_FAILED)
        
    def test_activities(self, ):
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        psids = []
        # создаем проект
        r = self.srequest(c, '/project/create', {'name' : 'proj1',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'init'},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid = resp['psid']
        puuid = resp['uuid']
        psids.append(psid)

        # создаем мероприятие
        r = self.srequest(c, '/activity/create', {'psid' : psid,
                                                  'name' : 'activ1',
                                                  'descr' : 'sdfafad',
                                                  'begin' : '2012-10-10T10:10:42',
                                                  'end' : '2020-10-10T10:10:44'},
                          httplib.CREATED)
        resp = dec.decode(r)
        auuid1 = resp['uuid']

        self.srequest(c, '/activity/create', {'psid' : psid,
                                              'name' : 'activ1',
                                              'begin' : '2012-10-10T10:10:42',
                                              'end' : '2020-10-10T10:10:44'},
                      httplib.PRECONDITION_FAILED)

        # публикуем мероприятие
        self.srequest(c, '/activity/public', {'psid' : psid,
                                              'uuid' : auuid1,
                                              'comment' : 'hoy!'},
                      httplib.CREATED)

        # просматриваем список мероприятий
        r = self.srequest(c, '/activity/list', {'psid' : psid},
                          httplib.OK)

        resp = dec.decode(r)
        self.assertEqual(1, len(resp))
        a = resp[0]
        self.assertEqual(a['uuid'], auuid1)
        self.assertEqual(a['name'], 'activ1')
        self.assertEqual(a['status'], 'accepted')
        self.assertEqual(a['votes'], [])

        # входим в мероприятие
        self.srequest(c, '/activity/participation', {'psid' : psid,
                                                     'action' : 'include',
                                                     'uuid' : auuid1},
                      httplib.CREATED)

        self.srequest(c, '/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)
        
        # приглашаем второго участника
        r = self.srequest(c, '/participant/invite', {'psid' : psid,
                                                     'name' : 'part2',
                                                     'descr' : 'blah blah'},
                          httplib.CREATED)
        resp = dec.decode(r)
        token2 = resp['token']

        r = self.srequest(c, '/participant/list', {'psid' : psid}, httplib.OK)
        prts = dec.decode(r)
        self.assertEqual(2, len(prts))
        uuid1 = [a['uuid'] for a in prts if a['name'] == 'part2'][0] # получили ид пользователя

        self.srequest(c, '/participant/vote/conform', {'psid' : psid,
                                                       'uuid' : uuid1,
                                                       'vote' : 'include'},
                      httplib.CREATED)

        # второй участник входит в проект
        r = self.srequest(c, '/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token2},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid2 = resp['psid']

        # второй участник входит в мероприятие
        r = self.srequest(c, '/activity/participation', {'psid' : psid2,
                                                         'action' : 'include',
                                                         'uuid' : auuid1},
                          httplib.CREATED)

        # просатриваем список участников мероприятий: смотрим чтобы было два
        # участника

        r = self.srequest(c, '/activity/participant/list', {'uuid' : auuid1},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set([p['uuid'] for p in prts]), set(resp))

        # второй участник создает мероприятие
        self.srequest(c, '/activity/create', {'psid' : psid2,
                                              'name' : 'activ2',
                                              'begin' : '2020-10-10T20:20:20', # вторая дата позднее
                                              'end' : '2010-10-10T20:20:20'},
                      httplib.PRECONDITION_FAILED)

        r = self.srequest(c, '/activity/create', {'psid' : psid2,
                                                  'name' : 'activ2',
                                                  'end' : '2020-10-10T20:20:20',
                                                  'begin' : '2010-10-10T20:20:20'},
                            httplib.CREATED)
        auuid2 = dec.decode(r)['uuid']

        # просмотр списка мероприятий двумя участниками: один видит созданное
        # мероприятие второй - нет
        r = self.srequest(c, '/activity/list', {'psid' : psid},
                          httplib.OK)
        self.assertEqual(1, len(dec.decode(r)))

        r = self.srequest(c, '/activity/list', {'psid' : psid2},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['created', 'accepted']), set([a['status'] for a in resp]))

        # публикация мероприятия участником
        self.srequest(c, '/activity/public', {'psid' : psid2,
                                              'uuid' : auuid2,
                                              'comment' : 'you ! this is a comment'},
                      httplib.CREATED)

        # снова список мероприятий, теперь инициатор видит учреждение как
        # предложенное для использования в роекте
        r = self.srequest(c, '/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['accepted', 'voted']), set([a['status'] for a in resp]))

        # подтверждение публикации инициатором
        self.srequest(c, '/activity/public', {'psid' : psid,
                                              'uuid' : auuid2},
                      httplib.CREATED)
        
        # теперь мероприятие видно как accepted
        r = self.srequest(c, '/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(set(['accepted']), set([a['status'] for a in resp]))

        # второй участник пытается удалить мероприятие и фейлится потому что
        # мероприятие уже согласовано
        self.srequest(c, '/activity/delete', {'psid' : psid2,
                                              'uuid' : auuid2},
                      httplib.PRECONDITION_FAILED)
        
        # теперь инициатор видит мероприятие как активное
        r = self.srequest(c, '/activity/list', {'psid' : psid},
                          httplib.OK)
        resp = dec.decode(r)
        self.assertEqual(2, len(resp))
        self.assertEqual(set(['accepted']), set([a['status'] for a in resp]))

        # второй участник создает еще одно мероприятие
        r = self.srequest(c, '/activity/create', {'psid' : psid2,
                                                  'name' : 'activ3',
                                                  'begin' : '2010-10-10T10:10:10',
                                                  'end' : '2010-10-11T10:10:10'},
                          httplib.CREATED)
        auuid3 = dec.decode(r)['uuid']

        # удаляет мероприяте
        self.srequest(c, '/activity/delete', {'psid' : psid2,
                                              'uuid' : auuid3},
                      httplib.CREATED)
        
        # просматривает список - мероприятия нет
        r = self.srequest(c, '/activity/list', {'psid' : psid2},
                          httplib.OK)
        self.assertEqual(2, len(dec.decode(r)))
        
        # второй участник предлагает удалить второе мероприятие
        self.srequest(c, '/activity/deny', {'psid' : psid2,
                                            'uuid' : auuid2},
                      httplib.CREATED)
        
        # в списке мероприятий появляется предложение на удаление мероприятия
        r = self.srequest(c, '/activity/list', {'psid' : psid2},
                          httplib.OK)

        resp = dec.decode(r)
        x = [r for r in resp if len(r['votes']) > 0]
        self.assertEqual(1, len(x))
        a = x[0]

        vt = a['votes'][0]
        self.assertEqual('exclude', vt['vote'])
        
        # инициатор подтверждает действие
        self.srequest(c, '/activity/deny', {'psid' : psid,
                                            'uuid' : auuid2},
                      httplib.CREATED)
        
        # в списке мероприятий мероприяте меняет статус на "denied"
        r = self.srequest(c, '/activity/list', {'psid' : psid2},
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
        r = self.srequest(c, '/project/create', {'name' : 'proj1',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'asdf'},
                          httplib.CREATED)
        
        psid = dec.decode(r)['psid']
        puuid = dec.decode(r)['uuid']
        psids.append(psid)

        self.srequest(c, '/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)
        
        r = self.srequest(c, '/activity/create', {'psid' : psid,
                                                  'name' : 'newact',
                                                  'begin' : '2010-10-10T20:20:20',
                                                  'end' : '2010-10-11T20:20:20'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']
        self.srequest(c, '/activity/public', {'psid' : psid,
                                              'uuid' : auuid,
                                              'comment' : 'public'},
                      httplib.CREATED)

        # создаем параметр
        r = self.srequest(c, '/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par1',
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False)},
                          httplib.CREATED)
        p1 = dec.decode(r)['uuid']

        # фейлимся
        r = self.srequest(c, '/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par1', # создание параметра с тем же именем
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False)},
                          httplib.PRECONDITION_FAILED)

        # создаем еще один с ограниченным набором значений
        r = self.srequest(c, '/activity/parameter/create',
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
        self.srequest(c, '/activity/parameter/create', {'psid' : psid,
                                                        'uuid' : auuid,
                                                        'name' : 'par3',
                                                        'tp' : 'text',
                                                        'enum': enc.encode(True)}, # не указаны перечисляемые значения
                      httplib.PRECONDITION_FAILED)

        # создаем третий параметр
        r = self.srequest(c, '/activity/parameter/create', {'psid' : psid,
                                                            'uuid' : auuid,
                                                            'name' : 'par3',
                                                            'tp' : 'text',
                                                            'enum' : enc.encode(False),
                                                            'value' : 'this is the default value'},
                          httplib.CREATED)
        p3 = dec.decode(r)['uuid']

        # создаем параметр имя которого совпадает с именем типового параметра из фикстуры
        self.srequest(c, '/activity/parameter/create', {'psid' : psid,
                                                        'uuid' : auuid,
                                                        'name' : 'test asdf',
                                                        'tp' : 'text',
                                                        'enum' : enc.encode(False)},
                      httplib.CREATED)

        # просматриваем созданные параметры
        r = self.srequest(c, '/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        
        # просматриваем типовые параметры
        r = self.srequest(c, '/parameters/list', {}, httplib.OK)
        defprms = dec.decode(r)

        # создаем параметры из типовых и проверяем чтобы статус возврата был
        # фейловым на параметрах с тем же именем что уже есть
        for defprm in defprms:
            self.srequest(c, '/activity/parameter/create/fromdefault', {'psid' : psid,
                                                                        'uuid' : auuid,
                                                                        'default' : defprm['uuid']},
                          httplib.PRECONDITION_FAILED if (defprm['name'] in [a['name'] for a in prms]) else httplib.CREATED)

        # добавляем участника
        r = self.srequest(c, '/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'spiderman',
                                                     'user_id' : 'blah blah'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        # меняем первый параметр
        self.srequest(c, '/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p1,
                                                        'value' : 'newval'},
                      httplib.CREATED)

        # смотрим что значение поменялось в списке параметров
        r = self.srequest(c, '/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        val = [a['value'] for a in prms if a['uuid'] == p1][0]
        self.assertEqual(val, 'newval')

        # гость предлагает сменить значение первого параметра
        self.srequest(c, '/activity/parameter/change', {'psid' : psid2,
                                                        'uuid' : p1,
                                                        'value' : 'nextval',
                                                        'comment' : 'jff'},
                      httplib.CREATED)

        # проверяем что появилось предложение по этому параметру
        r = self.srequest(c, '/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        prm = [a for a in prms if a['uuid'] == p1][0]
        self.assertEqual(prm['value'], 'newval')
        self.assertEqual(1, len(prm['votes']))
        self.assertEqual('nextval', prm['votes'][0]['value'])

        # инициатор предлагает такое же значение и подтверждает
        self.srequest(c, '/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p1,
                                                        'value' : 'nextval',
                                                        'comment' : 'ok'},
                      httplib.CREATED)

        # проверяем что значение сменилось
        r = self.srequest(c, '/activity/parameter/list', {'psid' : psid,
                                                          'uuid' : auuid},
                          httplib.OK)
        prms = dec.decode(r)
        prm = [a for a in prms if a['uuid'] == p1][0]
        self.assertEqual([], prm['votes'])
        self.assertEqual('nextval', prm['value'])
        

        # Пробуем сменить значение параметра с ограниченным набором значений
        # на значение не из набора и фейлимся
        self.srequest(c, '/activity/parameter/change', {'psid' : psid,
                                                        'uuid' : p2,
                                                        'value' : '1111111'},
                      httplib.PRECONDITION_FAILED)

        for p in psids:
            self._delete_project(p)
        

    def test_self_deleting_test(self, ):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        r = self.srequest(c, '/project/create', {'name' : 'asdf',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'asdf'},
                          httplib.CREATED)
        resp = dec.decode(r)
        psid = resp['psid']
        puuid = resp['uuid']

        self.srequest(c, '/project/status/change', {'psid' : psid,
                                                    'status' : 'planning'},
                      httplib.CREATED)

        r = self.srequest(c, '/project/enter/open', {'uuid' : puuid,
                                                     'name' : 'blalajs',
                                                     'user_id' : 'jsjsjfs'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']
        token = dec.decode(r)['token']

        self.srequest(c, '/participant/exclude', {'psid' : psid2},
                      httplib.CREATED)

        self.srequest(c, '/project/enter/invitation', {'uuid' : puuid,
                                                           'token' : token},
                      httplib.PRECONDITION_FAILED)

        self._delete_project(psid)

    def test_resources(self, ):
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        psids = []
        r = self.srequest(c, '/project/create', {'name' : 'wow super project',
                                                 'sharing' : 'open',
                                                 'ruleset' : 'despot',
                                                 'user_name' : 'the god'},
                          httplib.CREATED)
        psid = dec.decode(r)['psid']
        psids.append(psid)
        puuid = dec.decode(r)['uuid']
        
        r = self.srequest(c, '/activity/create', {'psid' : psid,
                                                  'begin' : '2010-10-10',
                                                  'end' : '2010-10-10',
                                                  'name' : 'new activity'},
                          httplib.CREATED)
        auuid = dec.decode(r)['uuid']
        
        # создаем личный ресурс
        self.srequest(c, '/resource/create', {'psid' : psid,
                                              'name' : 'kolbasa',
                                              'units' : u'kg',
                                              'use' : 'personal',
                                              'site' : 'internal'},
                      httplib.CREATED)

        # ресурс виден в общем списке (не по мероприятию)
        r = self.srequest(c, '/activity/resource/list', {'psid' : psid},
                                                         
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

        r = self.srequest(c, '/activity/resource/include',
                          {'psid' : psid,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'need' : enc.encode(True),
                           'amount' : 100500},
                          httplib.CREATED)
            
        # проверяем что он добавлен
        r = self.srequest(c, '/activity/resource/list', {'psid' : psid,
                                                         'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, rs['amount']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # удаляем ресурс из мероприятия
        r = self.srequest(c, '/activity/resource/exclude',
                          {'psid' : psid,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'comment' : 'test'},
                          httplib.CREATED)

        # проверяем что он не на мероприятии
        r = self.srequest(c, '/activity/resource/list', {'psid' : psid,
                                                         'uuid' : auuid},
                          httplib.OK)
        self.assertEqual(0, len(dec.decode(r)))
        r = self.srequest(c, '/activity/resource/list', {'psid' : psid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # второй участник входит в проект
        self.srequest(c, '/project/status/change',
                      {'uuid' : puuid,
                       'status' : 'planning',
                       'psid' : psid},
                      httplib.CREATED)
            
        r = self.srequest(c, '/project/enter/open',
                          {'uuid' : puuid,
                           'name' : 'test user',
                           'user_id' : 'super user you you'},
                          httplib.CREATED)
        psid2 = dec.decode(r)['psid']

        # второй участник предлагает использовать ресурс в мероприятии
        r = self.srequest(c, '/activity/resource/include',
                          {'psid' : psid2,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'need' : enc.encode(True),
                           'comment' : 'Here is comment'},
                          httplib.CREATED, True)
        # предложение видно 
        r = self.srequest(c, '/activity/resource/list', {'psid' : psid,
                                                         'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [('personal', rs['use']),
                     (False, rs['used']),
                     (0, rs['amount']), # Для личного ресурса количество игнорируется при добавлении
                     (1, len(rs['votes'])),
                     ('include', rs['votes'][0]['vote']),
                     ('Here is comment', rs['votes'][0]['comment'])]:
            self.assertEqual(a, b)

        # инициатор подтверждает
        self.srequest(c, '/activity/resource/include',
                      {'psid' : psid,
                       'uuid' : personal['uuid'],
                       'activity' : auuid,
                       'need' : enc.encode(True),
                       'amount' : 9000},
                      httplib.CREATED)

        # проверяем что ресурс действительно снова используется
        r = self.srequest(c, '/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [(False, rs['used']),
                     (0, len(rs['votes']))]:
            self.assertEqual(a, b)

        # второй участник использует ресурс как личный
        r = self.srequest(c, '/participant/resource/use',
                          {'psid' : psid2,
                           'uuid' : personal['uuid'],
                           'activity' : auuid,
                           'amount' : 10},
                          httplib.CREATED)

        # второй участник видит что ресурс используется
        r = self.srequest(c, '/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [(True, rs['used']),
                     (10, rs['amount'])]:
            self.assertEqual(a, b)

        # второй участник убирает ресурс из личного пользования
        self.srequest(c, '/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : personal['uuid'],
                       'activity' : auuid,
                       'amount' : 0},
                      httplib.CREATED)

        # второй участник видит что он больше не использует этот ресурс
        r = self.srequest(c, '/activity/resource/list',
                          {'psid' : psid2,
                           'uuid' : auuid},
                          httplib.OK)
        rs = dec.decode(r)[0]
        for a, b in [(False, rs['used']),
                     (0, rs['amount'])]:
            self.assertEqual(a, b)

        # создаем общий ресурс
        self.srequest(c, '/resource/create',
                      {'psid' : psid,
                       'name' : 'vodka32',
                       'units' : u'литр',
                       'use' : 'common',
                       'site' : 'external'},
                      httplib.CREATED)

        # смотрим что такое есть
        r = self.srequest(c, '/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        rsrs = dec.decode(r)
        self.assertEqual(2, len(rsrs))
        common = [a for a in rsrs if a['use'] == 'common'][0]
        for a, b in [('vodka32', common['name']),
                     (u'литр', common['units'])]:
            self.assertEqual(a, b)
        
        
        # добавляем его в мероприятие
        self.srequest(c, '/actvivity/resource/include',
                      {'psid' : psid,
                       'uuid' : common['uuid'],
                       'activity' : auuid,
                       'need' : enc.encode(True),
                       'amount' : 10,
                       'comment' : 'good vodka'},
                      httplib.CREATED)

        # видим что ресурс используется
        r = self.srequest(c, '/activity/resource/list',
                          {'psid' : psid,
                           'uuid' : auuid},
                          httplib.OK)
        rsrs = dec.decode(r)
        self.assertEqual(2, len(rsrs))
        rs = [a for a in rsrs if a['use'] == 'common'][0]
        for a, b in [(True, rs['used']),
                     (10, rs['amount'])]:
            self.assertEqual(a, b)
        

        # второй участник пытается использовать общий ресурс как личный и
        # фейлится
        self.srequest(c, '/participant/resource/use',
                      {'psid' : psid2,
                       'uuid' : common['uuid'],
                       'activity' : auuid,
                       'amount' : 100},
                      httplib.PRECONDITION_FAILED)




                                                  

        for p in psids:
            self._delete_project(p)
        
        

if __name__ == '__main__':
    main()
