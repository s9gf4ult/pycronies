# -*- coding: utf-8 -*-

from django.db import models
from datetime import date, datetime

# Create your models here.


class Project(models.Model):
    """Проект
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
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
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
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
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    accept = models.BooleanField()

class Resource(models.Model):
    """Ресурс проекта
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
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
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
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
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    vote = models.CharField(max_length=40)

class Parameter(models.Model):
    """Описание параметра
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
    name = models.SlugField()
    descr = models.TextField()
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()

class Param(models.Model):
    """Параметр
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True)
    creation_date = models.DateTimeField(default=datetime.new, null=False)
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


    
    
    
        
