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
        self.assertEqual(r4.status, httplib.NOT_FOUND)
        
if __name__ == '__main__':
    main()
