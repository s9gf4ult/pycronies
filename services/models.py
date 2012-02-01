# -*- coding: utf-8 -*-

from django.db import models
from datetime import date, datetime
import uuid

# Create your models here.

def hex4():
    """Return hexdigest of uuid4
    """
    return str(uuid.uuid4())


class Project(models.Model):
    """Проект
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    sharing = models.BooleanField()
    ruleset = models.CharField(max_length=20)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=20)

class Activity(models.Model):
    """Мероприятие
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length = 100)
    descr = models.TextField(null=True)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    accept = models.BooleanField()

class Participant(models.Model):
    """Участрник проекта
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    accept = models.BooleanField()

class Resource(models.Model):
    """Ресурс проекта
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    product = models.CharField(max_length=100) # FIXME: Это должна быть ссылка на продукт !!!
    name = models.CharField(max_length=100)
    descr = models.TextField()
    measure = models.CharField(max_length=40) # FIXME: Может это будет ссылка на элемент таблицы "еденицы измерения" ?
    usage = models.CharField(max_length=40)
    site = models.CharField(max_length=40)
    
class ActRes(models.Model):
    """Ресурс мероприятия или личный участника мероприятия
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, null=True, on_delete = models.CASCADE)
    resource = models.ForeignKey(Resource)
    vote = models.CharField(max_length=40, null=True) # можно null ?
    required = models.BooleanField()
    amount = models.DecimalField(max_digits=20, decimal_places = 2)
    accept = models.BooleanField()

class ActPart(models.Model):
    """Участник мероприятия
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    vote = models.CharField(max_length=40)

class Parameter(models.Model):
    """Описание параметра
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    name = models.SlugField()
    descr = models.TextField()
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()
    default_value = models.CharField(max_length=40)

class Param(models.Model):
    """Параметр
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    creation_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    parameter = models.ForeignKey(Parameter)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    level = models.CharField(max_length=40)
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()
    
class ParamVl(models.Model):
    """Значение параметра
    """
    param = models.ForeignKey(Param)
    value = models.CharField(max_length=40)
    caption = models.TextField()

class ParameterVL(models.Model):
    """Возможное значение описания параметра
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    parameter = models.ForeignKey(Parameter)
    value = models.CharField(max_length=40)
    caption = models.TextField()

class ParamVal(models.Model):
    """Значения параметра
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    param = models.ForeignKey(Param)
    participant = models.ForeignKey(Participant, null=True)
    value = models.CharField(max_length=40)
    caption = models.TextField()
    datetime = models.DateTimeField()
    opened = models.BooleanField()
    level = models.CharField(max_length=40)

class PartContakt(models.Model):
    """Контакт участника проекта
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    participant = models.ForeignKey(Participant)
    tp = models.CharField(max_length = 40)
    contact = models.CharField(max_length=40)

class PartAccept(models.Model):
    """Предложение участника в проект
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    participant = models.ForeignKey(Participant)
    acceptant = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
    vote = models.CharField(max_length=40)
    datetime = models.DateTimeField(default=datetime.now)

class Vote(models.Model):
    """Голос участника
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    participant = models.ForeignKey(Participant)
    parameter = models.ForeignKey(Parameter)
    acceptant = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
    voter = models.ForeignKey(Participant, related_name = 'voter_%(class)s_set')
    obj = models.CharField(max_length=40)
    vote = models.CharField(max_length=40)
