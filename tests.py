#!/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main
import httplib
import json

host = '127.0.0.1'
port = 8000

def getencdec():
    """
    """
    return (json.JSONEncoder(), json.JSONDecoder())

from services.common import dict2datetime
import datetime

class mytest(TestCase):
    """
    """

    def test_create_project(self, ):
        """
        """
        c = httplib.HTTPConnection(host, port)
        enc, dec = getencdec()
        p1 = enc.encode({'name' : u'Новый проект',
                         'descr' : 'blah blah, something here',
                         'begin_date' : {'year' : 2012,
                                         'month' : 3,
                                         'day' : 20,
                                         'hour' : 20,
                                         'minute' : 40,
                                         'second' : 22},
                         'sharing' : True,
                         'ruleset' : 'despot',
                         'user_name' : u'Вася',
                         'user_id' : 'some_id',
                         'user_descr' : u'местный дурачек'})
        c.request('POST', '/project/create', p1)
        r1 = c.getresponse()
        self.assertEqual(r1.status, httplib.CREATED)
        p2 = enc.encode({'descr' : 'blah blah, something here',
                         'begin_date' : {'year' : 2012,
                                         'month' : 3,
                                         'day' : 20,
                                         'hour' : 20,
                                         'minute' : 40,
                                         'second' : 22},
                         'sharing' : True,
                         'ruleset' : 'despot',
                         'user_name' : u'Вася',
                         'user_id' : 'some_id',
                         'user_descr' : u'местный дурачек'})
        c.request('POST', '/project/create', p2)
        r2 = c.getresponse()
        self.assertEqual(r2.status, httplib.PRECONDITION_FAILED)
        self.assertIsInstance(dec.decode(r2.read()), basestring)
        p3 = enc.encode({'name' : 'jsij',
                         'descr' : 'blah blah, something here',
                         'begin_date' : {'year' : 2012,
                                         'month' : 3,
                                         'hour' : 20,
                                         'minute' : 40,
                                         'second' : 22},
                         'sharing' : True,
                         'ruleset' : 'despot',
                         'user_id' : 'some_id',
                         'user_descr' : u'местный дурачек'})
        c.request('POST', '/project/create', p3)
        r3 = c.getresponse()
        self.assertEqual(r3.status, httplib.PRECONDITION_FAILED)

        c.request('GET', '/project/create', p3)
        r4 = c.getresponse()
        self.assertEqual(r4.status, httplib.NOT_IMPLEMENTED)

    def test_list_projects(self, ):
        """check list projects
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        for x in range(0, 50):
            c.request('POST', '/project/create', enc.encode({'name' : u'test project {0}'.format(x),
                                                            'descr' : u'description blah blah',
                                                            'begin_date' : {'year' : 2012,
                                                                            'month' : 3,
                                                                            'day' : 13,
                                                                            'hour' : 12,
                                                                            'minute' : 12,
                                                                            'second' : x},
                                                            'sharing' : True,
                                                            'ruleset' : 'despot',
                                                            'user_name' : u'Spiderman'}))
            r = c.getresponse()
            self.assertEqual(r.status, httplib.CREATED)
        # пробуем посмотреть все проекты
        c.request('POST', '/project/list', enc.encode({}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertTrue(len(resp) >= 50) # мы не знаем выполнился ли тест на создание проектов раньше

        # пробуем посмотреть проекты по строке поиска
        c.request('POST', '/project/list', enc.encode({'search' : 'test project'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertTrue(len(resp) >= 50)
        for pr in resp:
            self.assertTrue(('test project' in pr['name']) or ('test project' in pr['descr']))

        # запрашиваем проекты по дате
        c.request('POST', '/project/list', enc.encode({'begin_date' : {'year' : 2012,
                                                                       'month' : 3,
                                                                       'day' : 13,
                                                                       'hour' : 12,
                                                                       'minute' : 12,
                                                                       'second' : 30}})) # пропускаем первые 30 по дате
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertTrue(len(resp) >= 20)
        for pr in resp:
            self.assertTrue(dict2datetime(pr['begin_date']) >= datetime.datetime(2012, 3, 13, 12, 12, 30))

        # пробуем пролистать страницами по 5 проектов на страницу
        for pn in range(0, 12): # должно быть 10 страниц +1 если другие тесты выполнились раньше
            c.request('POST', '/project/list', enc.encode({'page_number' : pn,
                                                           'projects_per_page' : 5}))
            r = c.getresponse()
            self.assertEqual(r.status, httplib.OK)
            resp = dec.decode(r.read())
            if pn == 11:        # последняя страница пустая
                self.assertEqual(0, len(resp))
            else:
                self.assertTrue(len(resp) <= 5)

        # пробуем искать проекты которых нету
        c.request('POST', '/project/list', enc.encode({'search' : '11111111111111'})) # таких названий или описаний в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        self.assertEqual(0, len(dec.decode(r.read())))

    def test_list_user_projects_route(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        c.request('POST', '/project/create', enc.encode({'name' : 'test',
                                                         'sharing' : True,
                                                         'ruleset' : 'despot',
                                                         'user_name' : 'mega_user',
                                                         'user_id' : 'test_id'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        c.request('POST', '/project/list/userid', enc.encode('test_id'))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        resp = dec.decode(r.read())
        self.assertEqual(1, len(resp))
        self.assertEqual(resp[0]['name'], 'test')
        self.assertEqual(resp[0]['initiator'], True)
        self.assertEqual(resp[0]['status'], 'opened')

        c.request('POST', '/project/list/userid', enc.encode('11111111111')) # такого ид в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)

    def test_change_project_status(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        c.request('POST', '/project/create', enc.encode({'name' : 'something',
                                                         'sharing' : True,
                                                         'ruleset' : 'despot',
                                                         'user_name' : 'user name'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        c.request('POST', '/project/status/change', enc.encode({'psid' : psid, # все нормально
                                                                'status' : 'planning'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)

        c.request('POST', '/project/status/change', enc.encode({'psid' : psid,
                                                                'status' : 'blah blah'})) # не верный статус
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED) # должны зафейлиться

        c.request('POST', '/project/create', enc.encode({'name' : 'ajsdfasd',
                                                         'sharing' : True,
                                                         'ruleset' : 'vote', # создаем не управляемый проект
                                                         'user_name' : 'someuser'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        psid = dec.decode(r.read())['psid']

        c.request('POST', '/project/status/change', enc.encode({'psid' : psid, # пробуем этот проект изменить
                                                                'status' : 'planning'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)
        c.request('POST', '/project/status/change', enc.encode({'psid' : 'aisjdf', # не верный psid
                                                                'status' : 'planning'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)

    def test_create_project_parameter(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        c.request('POST', '/project/create', enc.encode({'name' : 'test project',
                                                         'sharing' : False,
                                                         'ruleset' : 'despot',
                                                         'user_name' : 'name blah blah'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)
        resp = dec.decode(r.read())
        psid = resp['psid']

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name',
                                                                   'tp' : 'text',
                                                                   'enum' : False,
                                                                   'value' : 'blah blah'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 1',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 'fufuf',
                                                                   'values' : [{'value' : 'you you you',
                                                                                'caption' : 'blah blah'},
                                                                               {'value' : 'fufuf'}]}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 2',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 'blah blah'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        # c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
        #                                                            'name' : 'parameter test name 3',
        #                                                            'tp' : 'text',
        #                                                            'value' : 'sdf',
        #                                                            'enum' : False}))
        # r = c.getresponse()
        # self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 4',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 23,
                                                                   'values' : [{'values' : 23}]}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 5',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 'avasd',
                                                                   'values' : [{'value' : 'avasd',
                                                                                'caption' : 'asidf'},
                                                                               {'value' : 'sijsji',
                                                                                'caption' : 234}]}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : 'sdf',
                                                                   'name' : 'parameter test name 6',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 'fufuf',
                                                                   'values' : [{'value' : 'you you you',
                                                                                'caption' : 'blah blah'},
                                                                               {'value' : 'fufuf'}]}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.NOT_FOUND)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name', # must fail - same name of parameter
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'value' : 'fufuf',
                                                                   'values' : [{'value' : 'you you you',
                                                                                'caption' : 'blah blah'},
                                                                               {'value' : 'fufuf'}]}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 7',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'values' : [{'value' : 'you you you',
                                                                                'caption' : 'blah blah'},
                                                                               {'value' : 'fufuf'}],
                                                                   'value' : 'asdf'})) # value is not from given sequence
        r = c.getresponse()
        self.assertEqual(r.status, httplib.PRECONDITION_FAILED)

        c.request('POST', '/project/parameter/create', enc.encode({'psid' : psid,
                                                                   'name' : 'parameter test name 8',
                                                                   'tp' : 'text',
                                                                   'enum' : True,
                                                                   'values' : [{'value' : 'you you you',
                                                                                'caption' : 'blah blah'},
                                                                               {'value' : 'fufuf'}],
                                                                   'value' : 'fufuf',
                                                                   'descr' : 'asdf'}))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.CREATED)

    def test_create_project_parameter_from_default_route(self, ):
        """
        """
        enc, dec = getencdec()
        c = httplib.HTTPConnection(host, port)
        c.request("POST", "/parameters/list")
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        defparams = dec.decode(r.read()) # список default параметров
        c.request('POST', '/project/create', enc.encode({'name' : 'project blah blah',
                                                         'descr' : 'this is project',
                                                         'sharing' : True,
                                                         'ruleset' : 'despot',
                                                         'user_name' : 'kumare'}))
        r = c.getresponse()
        self.assertEqual(httplib.CREATED, r.status)
        resp = dec.decode(r.read())
        psid = resp['psid']
        c.request('POST', '/project/parameter/list', enc.encode(psid))
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        params = dec.decode(r.read()) # список параметров проекта
        for defpar in defparams:
            if defpar['name'] in [p['name'] for p in params]: # дефолт параметр уже есть в проекте (создан во время создания проекта)
                c.request('POST', '/project/parameter/create/fromdefault', enc.encode({'psid' : psid,
                                                                                       'uuid' : defpar['uuid']}))
                r = c.getresponse()
                self.assertEqual(httplib.PRECONDITION_FAILED, r.status)
            else:               # дефолт параметра нет в параметрах проекта
                c.request('POST', '/project/parameter/create/fromdefault', enc.encode({'psid' : psid,
                                                                                       'uuid' : defpar['uuid']}))
                r = c.getresponse()
                self.assertEqual(httplib.CREATED, r.status)
        # создали все параметры из дефолтных, теперь проверим что параметры проекта совпадают со списокм дефолтных параметров
        names = set([(p['name'], p['default']) for p in defparams]) # дефолт параметры в множество
        c.request('POST', '/project/parameter/list', enc.encode(psid))
        r = c.getresponse()
        self.assertEqual(httplib.OK, r.status)
        ppars = dec.decode(r.read())
        pnames = set([(p['name'], p['value']) for p in ppars]) # новые параметры проекта в множестве
        self.assertEqual(names, pnames)
                
                
        
        
        
        
        
        


if __name__ == '__main__':
    main()
