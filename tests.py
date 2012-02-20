#!/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main
import httplib, urllib
import json
from services.common import string2datetime
import datetime

host = '127.0.0.1'
port = 8000

def getencdec():
    """
    """
    return (json.JSONEncoder(), json.JSONDecoder())

def encodeparams(prms):
    return urllib.urlencode(prms)

def request(conn, route, data):
    conn.request('POST', route, encodeparams(data), {'Content-Type' : 'application/x-www-form-urlencoded; charset=utf-8'})

class mytest(TestCase):
    """
    """
    def _delete_project(self, psid):
        """
        Arguments:
        - `psid`:
        """
        c = httplib.HTTPConnection(host, port)
        request(c, '/project/delete', {'psid' : psid})
        r = c.getresponse()
        # print(r.read())
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
        self.assertEqual(resp[0]['status'], 'open')

        request(c, '/project/list/userid', {'user_id' : '11111111111'}) # такого ид в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)
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

        request(c, '/project/enter/open', {'uuid' : resp['project_uuid'],
                                           'name' : 'blah blah',
                                           'user_id' : 'something'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        d = dec.decode(r.read())
        self.assertIn('psid', d)
        self.assertIn('token', d)

        request(c, '/project/enter/open', {'uuid' : resp['project_uuid'],
                                           'name' : 'blah blah',
                                           'user_id' : 'sdfasdf'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)
        
        request(c, '/project/enter/open', {'uuid' : resp['project_uuid'],
                                           'name' : 'blahsdf blah',
                                           'user_id' : 'something'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        request(c, '/project/status/change', {'psid' : resp['psid'],
                                              'status' : 'contractor'})
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        request(c, '/project/enter/open', {'uuid' : resp['project_uuid'],
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

        request(c, '/project/enter/open', {'uuid' : resp['project_uuid'],
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


        request(c, '/project/list', {})
        r = c.getresponse()
        prs = dec.decode(r.read())['projects']
        self.assertEqual(set(['somename', 'somename2', 'somename3']),
                         set([a['name'] for a in prs]))
        for pr in psid:
            self._delete_project(pr)
        
        
        

if __name__ == '__main__':
    main()
