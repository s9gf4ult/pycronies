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
    PROJECT_STATUS=((u'opened', u'Проект открыт для изменения' ),)   # FIXME: Это не полный список статусов проекта
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
    ACTIVITY_STATUS=((u'voted', u'Мероприятие предложено для добавления'), # FIXME: Еще статусы ?
                     (u'accepted', u'Мероприятие используется в проекте'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = SafeTextField(default=None, null=False)
    descr = SafeTextField()
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=40, default=u'voted', choices=ACTIVITY_STATUS)

    class Meta:
        unique_together = (("project", "name"), )

class Participant(BaseModel):
    """Участрник проекта
    """
    PARTICIPANT_STATUS= ((u'accepted', u'Участник проекта активен'),
                         (u'denied', u'Участник проекта запрещен'),
                         (u'voted', u'Участник пректа предложен для участия в проекте'))
    project = models.ForeignKey(Project)
    is_initiator = models.BooleanField(default=False)
    user = models.CharField(max_length=40, null=True)   # FIXME: Это должна быть ссылка на пользюка, пока заглушка
    psid = models.CharField(max_length=40)
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')
    status = models.CharField(max_length=40, choices=PARTICIPANT_STATUS, default=u'accepted') # FIXME: Заменить на статус с возможными значениями как для ресурсов мероприятия ?
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
    RESOURCE_USAGE = ((u'personal', u'Можно использовать как личный ресурс'),
                      (u'common', u'Можно использовать только как общий'))
    project = models.ForeignKey(Project)
    product = models.CharField(max_length=100, null=True) # FIXME: Это должна быть ссылка на продукт !!!
    name = SafeCharField(max_length=100, null=False, default=None)
    descr = SafeTextField(default=u'')
    measure = models.ForeignKey(MeasureUnits)
    usage = models.CharField(max_length=40, choices=RESOURCE_USAGE)
    site = models.CharField(max_length=40)

    class Meta:
        unique_together = (("project", "product"),
                           ("project", "name"))

class ActivityParticipant(BaseModel):
    """Участник мероприятия
    """
    ACTIVITY_PARTICIPANT_STATUS=((u'voted', u'Участник мероприятия предложен к участию'),
                                 (u'accepted', u'Участник мероприятия допущен к участию'),
                                 (u'denied', u'Участник мероприятия не допущен к участию'))
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    status = models.CharField(max_length=40, default=u'voted', choices=ACTIVITY_PARTICIPANT_STATUS)
    class Meta:
        unique_together = (("activity", "participant"), )

class ActivityParticipantVote(BaseModel):
    ACTIVITY_PARTICIPANT_VOTE=((u'include', u'Предложение о принятии в мероприятие участника'),
                               (u'exclude', u'Предложение об исключении участника из мероприятия'))
    voter = models.ForeignKey(Participant)
    activity_participnt = models.ForeignKey(ActivityParticipant)
    vote = models.CharField(max_length=40, choices=ACTIVITY_PARTICIPANT_VOTE, default=u'include')

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
    voter = models.ForeignKey(Participant)
    vote = models.CharField(max_length=40, null=False, default=None, choices = ACTIVITY_RESOURCE_VOTE)
    status = models.CharField(max_length=40, null=False, default=u'voted', choices = ACTIVITY_RESOURCE_VOTE_STATUS)

class ParticipantResource(BaseModel):
    """Личный ресурс участника мероприятия
    """
    participant = models.ForeignKey(ActivityParticipant)
    resource = models.ForeignKey(Resource)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=False, default=None)
    class Meta:
        unique_together = (("actpart", "resource"), )

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
    PARAMETER_VALUE_STATUS=((u'voted', u'Значение предложено'),
                            (u'accepted', u'Значение принято'),
                            (u'denied', u'Значение запрещено'))
    value = models.TextField()
    caption = SafeTextField(null=True)
    datatime = models.DateTimeField(null=True)
    status = models.CharField(max_length=40, choices=PARAMETER_VALUE_STATUS, default=u'voted')
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
class ResourceParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ResourceParameter)

class ParticipantParameter(BaseParameter):
    participant = models.ForeignKey(Participant)
class ParticipantParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ParticipantParameter)
class ParticipantParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ParticipantParameter)

class ParticipantContact(BaseModel):
    """Контакт участника проекта
    """
    participant = models.ForeignKey(Participant)
    tp = models.CharField(max_length = 40)
    contact = SafeTextField()

class ParticipantVote(BaseModel):
    """Предложение об участнике проекта
    """
    PARTICIPANT_VOTE_STATUS=((u'voted', u'Предложение открыто'),
                             (u'accepted', u'Предложение принято'),
                             (u'denied', u'Предложение отклонено'))
    PARTICIPANT_VOTE=((u'include', u'Предложение о добавлении участника в проект'), # FIXME: возможно какие то еще предложения над участником ?
                      (u'exclude', u'Предложение об удалении участника из проекта'))
    participant = models.ForeignKey(Participant)
    voter = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
    vote = models.CharField(max_length=40)
    status = models.CharField(max_length=40, default=u'voted', choices=PARTICIPANT_VOTE_STATUS)
    class Meta:
        unique_together((u'participant', u'voter'), )

# class Vote(BaseModel):
#     """Голос участника
#     """
#     project = models.ForeignKey(Project)
#     activity = models.ForeignKey(Activity)
#     resource = models.ForeignKey(Resource)
#     participant = models.ForeignKey(Participant)
#     parameter = models.ForeignKey(Parameter)
#     acceptant = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set')
#     voter = models.ForeignKey(Participant, related_name = 'voter_%(class)s_set')
#     obj = models.CharField(max_length=40)
#     vote = models.CharField(max_length=40)
