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

    def test_project_creation(self, ):
        """Test project creation and deletion
        """
        p = models.Project(name='somename')
        p.save()
        ps = models.Project.objects.all()
        self.assertEqual(p, ps[0])
        self.assertEqual(1, len(ps))
        p2 = models.Project()
        self.assertRaises(Exception, p2.save) # Project needs name

    def test_activity_creation(self, ):
        """Test activity creation
        """
        p = models.Project(name='someproj')
        p.save()
        a = models.Activity(name='act1', project = p)
        a.save()
        a2 = models.Activity(name='act1', project = p)
        s=transaction.savepoint()
        self.assertRaises(IntegrityError, a2.save) # because of same name in same project on insert
        transaction.savepoint_rollback(s)          # this works for postgresql, other db must work except mysql with MyIsam
        a2.name = 'act2'
        a2.save()
        a.name = 'act2'
        s=transaction.savepoint()
        self.assertRaises(IntegrityError, a.save)
        transaction.savepoint_rollback(s)

    def test_dict2datetime(self, ):
        """
        """
        a = datetime.datetime(2010, 3, 2, 20, 58, 44)
        d = {'year' : a.year,
             'month' : a.month,
             'day' : a.day,
             'hour' : a.hour,
             'minute' : a.minute,
             'second' : a.second}
        aa = dict2datetime(d)
        self.assertEqual(a, aa)

    def test_check_safe_string_or_null(self, ):
        """
        """
        self.assertEqual([], check_safe_string_or_null({}, 'a'))
        self.assertEqual([], check_safe_string_or_null({'a' : None}, 'a'))
        self.assertEqual([], check_safe_string_or_null({'a' : 'aasdifja'}, 'a'))
        self.assertEqual(1, len(check_safe_string_or_null({'a' : 34}, 'a')))
        self.assertEqual(1, len(check_safe_string_or_null({'a' : 'jsdif<script>asd'}, 'a')))

    def test_check_safe_string(self, ):
        """
        """
        self.assertEqual(1, len(check_safe_string({}, 'a')))
        self.assertEqual(1, len(check_safe_string({'a' : None}, 'a')))
        self.assertEqual([], check_safe_string({'a' : 'aasdifja'}, 'a'))
        self.assertEqual(1, len(check_safe_string({'a' : 34}, 'a')))
        self.assertEqual(1, len(check_safe_string({'a' : 'jsdif<script>asd'}, 'a')))

    def test_validate_datetime_dict(self, ):
        """
        """
        self.assertEqual(True, validate_datetime_dict({'year' : 2011,
                                                       'month' : 9,
                                                       'day' : 20,
                                                       'hour' : 20,
                                                       'minute' : 20,
                                                       'second' : 33}))
        self.assertEqual(False, validate_datetime_dict({'year' : 2011,
                                                        'month' : 9,
                                                        'day' : 20,
                                                        'hour' : 34,
                                                        'minute' : 20,
                                                        'second' : 33}))
        self.assertEqual(False, validate_datetime_dict({'month' : 9,
                                                        'day' : 20,
                                                        'hour' : 20,
                                                        'minute' : 20,
                                                        'second' : 33}))

    def test_check_datetime_or_null(self, ):
        """
        """
        self.assertEqual([], check_datetime_or_null({'a' : {'year' : 2011,
                                                            'month' : 9,
                                                            'day' : 20,
                                                            'hour' : 20,
                                                            'minute' : 20,
                                                            'second' : 33}}, 'a'))
        self.assertEqual([], check_datetime_or_null({'a' : None}, 'a'))
        self.assertEqual([], check_datetime_or_null({}, 'a'))
        self.assertEqual(1, len(check_datetime_or_null({'a' : {'year' : 2011,
                                                               'month' : 9,
                                                               'day' : 40,
                                                               'hour' : 20,
                                                               'minute' : 20,
                                                               'second' : 33}}, 'a')))
        self.assertEqual(1, len(check_datetime_or_null({'a' : 'asdfasdf'}, 'a')))

    def test_check_bool(self, ):
        """
        """
        self.assertEqual([], check_bool({'a': True}, 'a'))
        self.assertEqual(1, len(check_bool({'a' : 'True'}, 'a')))
        self.assertEqual(1, len(check_bool({}, 'a')))

    def test_check_string_or_null(self, ):
        """
        """
        self.assertEqual([], check_string_or_null({'a' : ' iasdf a'}, 'a'))
        self.assertEqual([], check_string_or_null({'a' : None}, 'a'))
        self.assertEqual([], check_string_or_null({}, 'a'))
        self.assertEqual(1, len(check_string_or_null({'a' : 23}, 'a')))

    def test_check_string(self, ):
        """
        """
        self.assertEqual([], check_string({'a' : 'asdfasd'}, 'a'))
        self.assertEqual(1, len(check_string({'a' : None}, 'a')))
        self.assertEqual(1, len(check_string({}, 'a')))
        self.assertEqual(1, len(check_string({'a' : 23}, 'a')))

    def test_check_string_choise(self, ):
        """
        """
        self.assertEqual([], check_string_choise({'a' : 'a'}, 'a', ['er', 'sdj', 'a', 'efef']))
        self.assertEqual(1, len(check_string_choise({'a' : 23}, 'a', ['a', '23', 23, 'iadf'])))
        self.assertEqual(1, len(check_string_choise({}, 'a', ['234', 'sdf'])))
        self.assertEqual(1, len(check_string_choise({'a' : 'a'}, 'a', [])))
        
    def test_check_int_or_null(self, ):
        """
        """
        self.assertEqual([], check_int_or_null({'a' : 34}, 'a'))
        self.assertEqual([], check_int_or_null({}, 'a'))
        self.assertEqual([], check_int_or_null({'a' : None}, 'a'))
        self.assertEqual(1, len(check_int_or_null({'a' : '3'}, 'a')))

    def test_check_string_choise_or_null(self, ):
        """
        """
        self.assertEqual([], check_string_choise_or_null({}, 'a', ['a', 'b']))
        self.assertEqual([], check_string_choise_or_null({'a' : None}, 'a', ['a', 'b']))
        self.assertEqual([], check_string_choise_or_null({'a' : 'a'}, 'a', ['a', 'b']))
        self.assertEqual(1, len(check_string_choise_or_null({'a' : 2}, 'a', [2, '2', 'a'])))
        self.assertEqual(1, len(check_string_choise_or_null({'a' : '2'}, 'a', [2, 'a'])))

    def test_datetime2dict_and_back(self, ):
        """
        """
        dd = datetime.datetime(2030, 8, 27, 4, 44, 20)
        dct = datetime2dict(dd)
        dd2 = dict2datetime(dct)
        self.assertEqual(dd, dd2)

    def test_check_list_or_null(self, ):
        """
        """
        self.assertEqual([], check_list_or_null({'a': [1, 3,4]}, 'a'))
        self.assertEqual([], check_list_or_null({}, 'a'))
        self.assertEqual(1, len(check_list_or_null({'a' : 'list'}, 'a')))

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
        
