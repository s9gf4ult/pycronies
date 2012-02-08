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
                         'description' : 'blah blah, something here',
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
                         'user_description' : u'местный дурачек'})
        c.request('POST', '/project/create', p1)
        r1 = c.getresponse()
        self.assertEqual(r1.status, httplib.CREATED)
        p2 = enc.encode({'description' : 'blah blah, something here',
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
                         'user_description' : u'местный дурачек'})
        c.request('POST', '/project/create', p2)
        r2 = c.getresponse()
        self.assertEqual(r2.status, httplib.PRECONDITION_FAILED)
        self.assertEqual(1, len(dec.decode(r2.read())))
        p3 = enc.encode({'name' : 'jsij',
                         'description' : 'blah blah, something here',
                         'begin_date' : {'year' : 2012,
                                         'month' : 3,
                                         'hour' : 20,
                                         'minute' : 40,
                                         'second' : 22},
                         'sharing' : True,
                         'ruleset' : 'despot',
                         'user_id' : 'some_id',
                         'user_description' : u'местный дурачек'})
        c.request('POST', '/project/create', p3)
        r3 = c.getresponse()
        self.assertEqual(r3.status, httplib.PRECONDITION_FAILED)
        self.assertEqual(2, len(dec.decode(r3.read())))

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
                                                            'description' : u'description blah blah',
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
        c.request('POST', '/project/list', enc.encode({'search' : '11111111111111'})) # такиз названий или описаний в базе нет
        r = c.getresponse()
        self.assertEqual(r.status, httplib.OK)
        self.assertEqual(0, len(dec.decode(r.read())))



if __name__ == '__main__':
    main()
