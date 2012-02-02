# -*- coding: utf-8 -*-

from django.db import models
from datetime import date, datetime
import uuid
import re

# Create your models here.

class SafeTextField(models.TextField):
    def get_prep_value(self, value):
        """Validate value and return prepared
        Arguments:
        - `value`:
        """
        if re.search('[<>]', value):
            raise models.validators.ValidationError('Text field must not contain < or > symbols')
        return super(SafeTextField, self).get_prep_value(value)

class SafeCharField(models.SlugField):
    def get_prep_value(self, value):
        """Validate field and return prepared value
        Arguments:
        - `value`:
        """
        if re.search('[<>]', value):
            raise models.validators.ValidationError('Text field must not contain < or > symbols')
        return super(SafeCharField, self).get_prep_value(value)

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
    PROJECT_RULESET=((u'despot', u'Проект управляется инициатором'),
                     (u'vote', u'Проект управляется голосованием'),
                     (u'auto', u'Проект управляется автоматически'))
    PROJECT_STATUS=((, ), )               # FIXME: написать какие статусы у проекта бывают
    name = SafeCharField(max_length=100, default=None)
    descr = SafeTextField(default=u'')
    sharing = models.BooleanField()
    ruleset = models.CharField(max_length=40, default='despot', null=False, choices=PROJECT_RULESET)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=40, null=False, choices=PROJECT_STATUS)

class Activity(BaseModel):
    """Мероприятие
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = SafeCharField(max_length=100)
    descr = SafeTextField()
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    accept = models.BooleanField()

    class Meta:
        unique_together = (("project", "name"), )

class Participant(BaseModel):
    """Участрник проекта
    """
    project = models.ForeignKey(Project)
    is_initiator = models.BooleanField(default=False)
    user = models.CharField(max_length=40, null=True)   # FIXME: Это должна быть ссылка на пользюка, пока заглушка
    psid = models.CharField(max_length=40)
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')
    accept = models.BooleanField()        # FIXME: Заменить на статус с возможными значениями как для ресурсов мероприятия ?
    last_login = models.DateTimeField(null=True)

    class Meta:
        unique_together = (("project", "name"), )

class MeasureUnits(BaseModel):
    """Еденицы измерения количества ресурса
    """
    name = SafeCharField(max_length=50)
    descr = SafeTextField()

class Resource(BaseModel):
    """Доступный ресурс проекта
    """
    USAGE_CHOISES = ((u'personal', u'Можно использовать как личный ресурс'),
                     (u'common', u'Можно использовать только как общий'))
    project = models.ForeignKey(Project)
    product = models.CharField(max_length=100, null=True) # FIXME: Это должна быть ссылка на продукт !!!
    name = SafeCharField(max_length=100, null=False, default=None)
    descr = SafeTextField(default=u'')
    measure = models.ForeignKey(MeasureUnits)
    usage = models.CharField(max_length=40, choices=USAGE_CHOISES)
    site = models.CharField(max_length=40)

    class Meta:
        unique_together = (("project", "product"),
                           ("project", "name"))

class ActivityParticipant(BaseModel):
    """Участник мероприятия
    """
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    accept = models.BooleanField(default = False)
    vote = models.CharField(max_length=40)   # FIXME: Заменить на статус с возможными значениями как в ресурсах мероприятия ?
    class Meta:
        unique_together = (("activity", "participant"), )

class ActivityResource(BaseModel):
    """Ресурс мероприятия
    """
    ACTIVITY_RESOURCE_STATUS=((u'accepted', u'Ресурс доступен в мероприятии'),
                              (u'denied', u'Ресурс исключен из мероприятия'),
                              (u'voted', u'Ресурс предложен для использования в мероприятии'))
    activity = models.ForeignKey(Activity)
    resource = models.ForeignKey(Resource)
    required = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=False, default=None) # NOTE: так как за количество ресурса в мероприятии тоже будут голосовать, а таблица голосов содержит ForeignKey на параметр ресурса, то может количество тоже сделать параметром ресурса ??
    status = models.CharField(max_length=40, default=u'voted', choices=ACTIVITY_RESOURCE_STATUS)
    class Meta:
        unique_together = (("activity", "resource"), )

class ParticipantResource(BaseModel):
    """Личный ресурс участника мероприятия
    """
    actpart = models.ForeignKey(ActivityParticipant)
    resource = models.ForeignKey(Resource)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=False, default=None)
    class Meta:
        unique_together = (("actpart", "resource"), )

class ActivityResourceVote(BaseModel):
    """Предложение на включение ресурса в мероприятие
    """
    ACTIVITY_RESOURCE_VOTE = ((u'include', u'Включить ресурс в мероприятие'),
                              (u'exclude', u'Исключить ресурс из мероприятия'),
                              (u'add', u'Добавить или отнять количество ресурса'))
    ACTIVITY_RESOURCE_VOTE_STATUS = ((u'voted', u'Предложено'),
                                     (u'accepted', u'Принято'),
                                     (u'denied', u'Отклонено'),
                                     (u'imposed', u'Вынесено на голосование'))
    resource = models.ForeignKey(ActivityResource)
    participant = models.ForeignKey(Participant)
    vote = models.CharField(max_length=40, null=False, default=None, choices = ACTIVITY_RESOURCE_VOTE)
    status = models.CharField(max_length=40, null=False, default=u'voted', choices = ACTIVITY_RESOURCE_VOTE_STATUS)

# class ActRes(BaseModel):
#     """Ресурс мероприятия или личный участника мероприятия
#     """
#     project = models.ForeignKey(Project)
#     activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
#     participant = models.ForeignKey(ActPart, null=True, on_delete = models.CASCADE)
#     resource = models.ForeignKey(Resource)
#     vote = models.CharField(max_length=40, null=True)   # NOTE:  можно null ?
#     required = models.BooleanField(default=False)
#     amount = models.DecimalField(max_digits=20, decimal_places = 2, null=False, default=None)
#     accept = models.BooleanField()

#     class Meta:
#         unique_together = (("project", "activity", "participant", "resource"), )

class DefaultParameter(BaseModel):
    """Предлагаемый параметр
    """
    name = SafeCharField(max_length=100, default=None)
    descr = SafeTextField(default=u'')
    tp = models.CharField(max_length=40)
    enum = models.BooleanField(default = False)
    default_value = models.CharField(max_length=40, default=None)

class DefaultParameterVl(BaseModel):
    """Перечисляемое значение предлагаемого параметра
    """
    parameter = models.ForeignKey(DefaultParameter)
    value = models.CharField(max_length=40, default=None, null=False)
    caption = models.TextField()

class BaseParameter(BaseModel):
    """Базовый класс для параметров
    """
    default_parameter = models.ForeignKey(DefaultParameter, null=True)
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()
    class Meta:
        abstract = True

class BaseParameterVl(BaseModel):
    """Базовый класс перечисляемых значений параметра
    """
    value = models.CharField(max_length=40)
    caption = models.TextField()
    class Meta:
        abstract = True

class BaseParameterVal(BaseModel):
    """Базовый класс значения параметра
    """
    value = models.CharField(max_length=40)
    caption = models.TextField()
    opened = models.BooleanField()
    class Meta:
        abstract = True

class ProjectParameter(BaseParameter):
    project = models.ForeignKey(Project)
class ProjectParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ProjectParameter)
class ProjectParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ProjectParameter)

class ActivityParameter(BaseParameter):
    activity = models.ForeignKey(Activity)
class ActivityParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ActivityParameter)
class ActivityParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ActivityParameter)

class ResourceParameter(BaseParameter):
    resource = models.ForeignKey(Resource)
class ResourceParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ResourceParameter)
class ResourceParameterVal(BaseParameterVal)

class ParticipantParameter(BaseParameter):
    participant = models.ForeignKey(Participant)
class ParticipantParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ParticipantParameter)
class ParticipantParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ParticipantParameter)

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
