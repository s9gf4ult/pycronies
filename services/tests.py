"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
from django.test import TestCase
from django.db import IntegrityError, transaction
from services import models
from services.common import dict2datetime, check_safe_string_or_null, check_safe_string, \
    validate_datetime_dict, check_datetime_or_null, check_bool, check_string, check_string_choise, \
    check_string_or_null, check_int_or_null, check_string_choise_or_null, dict2datetime, datetime2dict, \
    check_list_or_null, get_or_create_object


class SimpleTest(TestCase):


    def test_get_or_create_object(self, ):
        p = get_or_create_object(models.Project, {'name' : 'blah blah'}, {'descr' : '111', 'sharing' : 'open', 'ruleset' : 'despot'})
        self.assertIsInstance(p, models.Project)
        pp = get_or_create_object(models.Project, {'name' : 'blah blah'}, {'descr' : '234'})
        self.assertEqual(p.uuid, pp.uuid)
        self.assertEqual(pp.descr, '234')
        prt = get_or_create_object(models.Participant, {'name' : 'part1', 'project' : pp})
        prt2 = get_or_create_object(models.Participant, {'name' : 'part1', 'project' : pp}, {'descr' : 'asdf'})
        self.assertEqual(prt.uuid, prt2.uuid)
        prt3 = get_or_create_object(models.Participant, {'name' : 'part1', 'project' : pp}, {'descr' : 'ijsji'}, (lambda p: False))
        self.assertEqual(None, prt3)
        
