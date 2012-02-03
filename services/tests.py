"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from services import models
from django.db import IntegrityError, transaction

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
        
