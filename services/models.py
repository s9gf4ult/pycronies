# -*- coding: utf-8 -*-

from django.db import models
from datetime import date, datetime
import uuid

# Create your models here.

def hex4():
    """Return hexdigest of uuid4
    """
    return str(uuid.uuid4())

class BaseModel(models.Model):
    """Все объекты в базе имеют поля uuid и create_date, а также один и тот же метод __unicode__
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4)
    create_date = models.DateTimeField(default=datetime.now, null=False)
    def __unicode__(self, ):
        """Return uuid
        """
        return self.uuid

    class Meta:
        abstract = True

class Project(BaseModel):
    """Проект
    """
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    sharing = models.BooleanField()
    ruleset = models.CharField(max_length=20)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=20)

class Activity(BaseModel):
    """Мероприятие
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length = 100)
    descr = models.TextField(null=True)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    accept = models.BooleanField()

    class Meta:
        unique_together = (("project", "name"), )

class Participant(BaseModel):
    """Участрник проекта
    """
    user = models.CharField(max_length=40, null=True)   # FIXME: Это должна быть ссылка на чето, пока заглушка
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    accept = models.BooleanField()

    class Meta:
        unique_together = (("project", "name"), )

class Resource(BaseModel):
    """Ресурс проекта
    """
    project = models.ForeignKey(Project)
    product = models.CharField(max_length=100, null=True) # FIXME: Это должна быть ссылка на продукт !!!
    name = models.CharField(max_length=100)
    descr = models.TextField()
    measure = models.CharField(max_length=40) # FIXME: Может это будет ссылка на элемент таблицы "еденицы измерения" ?
    usage = models.CharField(max_length=40)
    site = models.CharField(max_length=40)
    
    class Meta:
        unique_together = (("project", "product"),
                           ("project", "name"))

class ActPart(BaseModel):
    """Участник мероприятия
    """
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    vote = models.CharField(max_length=40)
    
class ActRes(BaseModel):
    """Ресурс мероприятия или личный участника мероприятия
    """
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(ActPart, null=True, on_delete = models.CASCADE)
    resource = models.ForeignKey(Resource)
    vote = models.CharField(max_length=40, null=True)   # NOTE:  можно null ?
    required = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=20, decimal_places = 2, null=False, default=None)
    accept = models.BooleanField()

    class Meta:
        unique_together = (("project", "activity", "participant", "resource"), )

class Parameter(BaseModel):
    """Описание параметра
    """
    name = models.SlugField()
    descr = models.TextField()
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()
    default_value = models.CharField(max_length=40)

class Param(BaseModel):
    """Параметр
    """
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    parameter = models.ForeignKey(Parameter)
    name = models.CharField(max_length=100)
    descr = models.TextField(null=True)
    level = models.CharField(max_length=40)
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()

class ParamVl(BaseModel):
    """Значение параметра
    """
    param = models.ForeignKey(Param)
    value = models.CharField(max_length=40)
    caption = models.TextField()

class ParameterVL(BaseModel):
    """Возможное значение описания параметра
    """
    parameter = models.ForeignKey(Parameter)
    value = models.CharField(max_length=40)
    caption = models.TextField()

class ParamVal(BaseModel):
    """Значения параметра
    """
    param = models.ForeignKey(Param)
    participant = models.ForeignKey(Participant, null=True)
    value = models.CharField(max_length=40)
    caption = models.TextField()
    datetime = models.DateTimeField()
    opened = models.BooleanField()
    level = models.CharField(max_length=40)

class PartContakt(BaseModel):
    """Контакт участника проекта
    """
    participant = models.ForeignKey(Participant)
    tp = models.CharField(max_length = 40)
    contact = models.CharField(max_length=40)

class PartAccept(BaseModel):
    """Предложение участника в проект
    """
    participant = models.ForeignKey(Participant)
    acceptant = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
    vote = models.CharField(max_length=40)
    datetime = models.DateTimeField(default=datetime.now)

class Vote(BaseModel):
    """Голос участника
    """
    project = models.ForeignKey(Project)
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    participant = models.ForeignKey(Participant)
    parameter = models.ForeignKey(Parameter)
    acceptant = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
    voter = models.ForeignKey(Participant, related_name = 'voter_%(class)s_set')
    obj = models.CharField(max_length=40)
    vote = models.CharField(max_length=40)
