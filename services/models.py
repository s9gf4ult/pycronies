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
        if isinstance(value, basestring) and re.search('[<>]', value):
            raise models.validators.ValidationError('Text field must not contain < or > symbols')
        return super(SafeTextField, self).get_prep_value(value)

class SafeCharField(models.SlugField):
    def get_prep_value(self, value):
        """Validate field and return prepared value
        Arguments:
        - `value`:
        """
        if isinstance(value, basestring) and re.search('[<>]', value):
            raise models.validators.ValidationError('Text field must not contain < or > symbols')
        return super(SafeCharField, self).get_prep_value(value)

def hex4():
    """Return hexdigest of uuid4
    """
    return str(uuid.uuid4())

class BaseModel(models.Model):
    """Все объекты в базе имеют поля uuid и create_date, а также один и тот же метод __unicode__
    """
    uuid = models.CharField(max_length=40, primary_key=True, unique=True, default=hex4, db_index=True)
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
    PROJECT_STATUS=((u'opened', u'Проект открыт' ),
                    (u'planning', u'Проект на стадии планирования'),
                    (u'contractor', u'Выбор контрагента'),
                    (u'budget', u'Формирование бюджета'),
                    (u'control', u'Контроль'),
                    (u'closed', u'Закрыт'))
    PROJECT_SHARING = ((u'open', u'Проект открытый'),
                       (u'close', u'Проект закрытый'),
                       (u'invitation', u'Проект по приглашению'))
    name = SafeCharField(max_length=100, default=None, db_index=True, verbose_name="nom nom nom")
    descr = SafeTextField(default=u'', db_index=True)
    sharing = SafeCharField(max_length=40, choices=PROJECT_SHARING)
    ruleset = models.CharField(max_length=40, default='despot', null=False, choices=PROJECT_RULESET)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=40, null=False, choices=PROJECT_STATUS)
    class Meta:
        ordering = ['-begin_date']

class Activity(BaseModel):
    """Мероприятие
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = SafeTextField(default=None, null=False)
    descr = SafeTextField(default=u'')
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    class Meta:
        unique_together = (("project", "name"), )

class ActivityStatus(BaseModel):
    """Статус мероприятия"""
    ACTIVITY_STATUS=((u'created', u'Мероприятие создано'),
                     (u'voted', u'Мероприятие предложено для добавления'),
                     (u'accepted', u'Мероприятие используется в проекте'),
                     (u'denied', u'Мероприятие исключено'))
    ACTIVITY_STATUS_STATUS = ((u'voted', u'Статус мероприятия предложен'),
                              (u'accepted', u'Статус мероприятия активен'),
                              (u'denied', u'Статус мероприятия отклонен'),
                              (u'changed', u'Статус мероприятия изменен'))

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    value = models.CharField(max_length=40, choices=ACTIVITY_STATUS)
    status = models.CharField(max_length=40, choices=ACTIVITY_STATUS_STATUS)


class Participant(BaseModel):
    """Участрник проекта
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    dt = models.DateTimeField(default=None, null=True) # Дата последнего входа участника
    is_initiator = models.BooleanField(default=False)
    user = models.CharField(max_length=40, null=True)   # FIXME: Это должна быть ссылка на пользюка, пока заглушка
    psid = models.CharField(max_length=40, unique=True, null=True, default=None)
    token = models.CharField(max_length=40, null=True, unique=True)
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')

    class Meta:
        unique_together = (("project", "name"),
                           ("project", "user"))

class ActivityVote(BaseModel):
    """Предложение по мероприятию"""
    activity_status = models.ForeignKey(ActivityStatus, on_delete=models.CASCADE)
    voter = models.ForeignKey(Participant, on_delete=models.CASCADE)
    comment = SafeTextField(null=False, default=u'')


class ParticipantStatus(BaseModel):
    """Статус участника проекта
    """
    PARTICIPANT_STATUS = ((u'accepted', u'Участник проекта активен'),
                          (u'denied', u'Участник проекта запрещен'))
    PARTICIPANT_STATUS_STATUS = ((u'accepted', u'Активный статус участника проекта'),
                                 (u'voted', u'Предложенный статус участника'),
                                 (u'changed', u'Предыдущий статус участника'),
                                 (u'denied', u'Отклоненный статус участника'))
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    value = models.CharField(max_length=40, choices=PARTICIPANT_STATUS)
    status = models.CharField(max_length=40, choices=PARTICIPANT_STATUS_STATUS)

class MeasureUnits(BaseModel):
    """Еденицы измерения количества ресурса
    """
    name = SafeCharField(max_length=50)
    descr = SafeTextField(default=u'')

class Resource(BaseModel):
    """Доступный ресурс проекта
    """
    RESOURCE_USAGE = ((u'personal', u'Можно использовать как личный ресурс'),
                      (u'common', u'Можно использовать только как общий'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
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
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    class Meta:
        unique_together = (("activity", "participant"), )

class ActivityParticipantStatus(BaseModel):
    ACTIVITY_PARTICIPANT_STATUS=((u'accepted', u'Участник мероприятия допущен к участию'),
                                 (u'denied', u'Участник мероприятия не допущен к участию'))
    ACTIVITY_PARTICIPANT_STATUS_STATUS = ((u'accepted', u'Статус участника активен'),
                                          (u'voted', u'Предложение статуса'),
                                          (u'denied', u'Статус отклонен'),
                                          (u'changed', u'Статус изменен'))
    activity_participant = models.ForeignKey(ActivityParticipant, on_delete=models.CASCADE)
    status = models.CharField(max_length=40, choices = ACTIVITY_PARTICIPANT_STATUS_STATUS)
    value = models.CharField(max_length=40, choices = ACTIVITY_PARTICIPANT_STATUS)
        

class ActivityParticipantVote(BaseModel):
    voter = models.ForeignKey(Participant, on_delete=models.CASCADE)
    activity_particapnt_status = models.ForeignKey(ActivityParticipantStatus)
    comment = SafeTextField(null=False, default=u'')

class ActivityResource(BaseModel):
    """Ресурс мероприятия
    """
    ACTIVITY_RESOURCE_STATUS=((u'accepted', u'Ресурс доступен в мероприятии'),
                              (u'denied', u'Ресурс исключен из мероприятия'),
                              (u'voted', u'Ресурс предложен для использования в мероприятии'))
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
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
    resource = models.ForeignKey(ActivityResource, on_delete=models.CASCADE)
    voter = models.ForeignKey(Participant, on_delete=models.CASCADE)
    vote = models.CharField(max_length=40, null=False, default=None, choices = ACTIVITY_RESOURCE_VOTE)
    status = models.CharField(max_length=40, null=False, default=u'voted', choices = ACTIVITY_RESOURCE_VOTE_STATUS)

class ParticipantResource(BaseModel):
    """Личный ресурс участника мероприятия
    """
    participant = models.ForeignKey(ActivityParticipant, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=False, default=None)
    class Meta:
        unique_together = (("participant", "resource"), )

class DefaultParameter(BaseModel):
    """Предлагаемый параметр
    """
    name = SafeCharField(max_length=100, default=None)
    descr = SafeTextField(default=u'')
    tp = models.CharField(max_length=40)
    enum = models.BooleanField(default = False)
    default_value = models.CharField(max_length=40, default=None)
    tecnical = models.BooleanField(default=False)

class DefaultParameterVl(BaseModel):
    """Перечисляемое значение предлагаемого параметра
    """
    parameter = models.ForeignKey(DefaultParameter, on_delete=models.CASCADE)
    value = models.CharField(max_length=40, default=None, null=False)
    caption = models.TextField()
    class Meta:
        unique_together = (('value', 'parameter'), )

class ProjectRulesetDefaults(BaseModel): # соответствия свойств проекта дефолтным параметрам
    parameter = models.ForeignKey(DefaultParameter)
    ruleset = models.CharField(max_length=40, null=True, choices=Project.PROJECT_RULESET) # Если null значит для проектов с любым ruleset
    class Meta:
        unique_together = (('parameter', 'ruleset'))


# class DefaultProjectParameter(BaseModel):
#     """Предлагаемый параметр
#     """
#     ruleset = models.CharField(max_length=40, null=True, choices=Project.PROJECT_RULESET)
#     status = models.CharField(max_length=40, null=True, choices=Project.PROJECT_STATUS)
#     name = SafeCharField(max_length=100, default=None)
#     descr = SafeTextField(default=u'')
#     tp = models.CharField(max_length=40)
#     enum = models.BooleanField(default = False)
#     default_value = models.CharField(max_length=40, null=True, default=None)
#     class Meta:
#         unique_together=(('ruleset', 'name'), )

# class DefaultProjectParameterVl(BaseModel):
#     """Перечисляемое значение предлагаемого параметра
#     """
#     parameter = models.ForeignKey(DefaultProjectParameter, on_delete=models.CASCADE)
#     value = models.CharField(max_length=40, default=None, null=False)
#     caption = models.TextField()


class BaseParameter(BaseModel):
    """Базовый класс для параметров
    """
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')
    tp = models.CharField(max_length=40)
    enum = models.BooleanField()
    class Meta:
        abstract = True

class BaseParameterVl(BaseModel):
    """Базовый класс возможных значений параметра
    """
    value = models.CharField(max_length=40)
    caption = models.TextField(null=True)
    class Meta:
        abstract = True

class BaseParameterVal(BaseModel):
    """Базовый класс значения параметра
    """
    PARAMETER_VALUE_STATUS=((u'voted', u'Значение предложено'),
                            (u'accepted', u'Значение принято'),
                            (u'denied', u'Значение запрещено'),
                            (u'changed', u'Значение было изменено'))
    value = SafeTextField()
    caption = SafeTextField(null=True)
    dt = models.DateTimeField(null=True) # время начала действия значения
    status = models.CharField(max_length=40, choices=PARAMETER_VALUE_STATUS, default=u'voted')
    class Meta:
        abstract = True

class ProjectParameter(BaseParameter):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    default_parameter = models.ForeignKey(DefaultParameter, null=True, on_delete=models.SET_NULL)
    class Meta:
        unique_together = (('project', 'name'), )
class ProjectParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ProjectParameter, on_delete=models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )
class ProjectParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ProjectParameter, on_delete=models.CASCADE)

class ProjectParameterVote(BaseModel):
    PROJECT_PARAMETER_VOTE=(('change', u'Изменить значение параметра на указанное'),)
    voter = models.ForeignKey(Participant)
    parameter_val = models.ForeignKey(ProjectParameterVal, on_delete=models.CASCADE)
    vote = models.CharField(max_length=40, choices=PROJECT_PARAMETER_VOTE)
    class Meta:
        unique_together=(('voter', 'parameter_val'), )

class ActivityParameter(BaseParameter):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    default_parameter = models.ForeignKey(DefaultParameter, null=True, on_delete=models.SET_NULL)
class ActivityParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ActivityParameter, on_delete=models.CASCADE)
class ActivityParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ActivityParameter, on_delete=models.CASCADE)

class ResourceParameter(BaseParameter):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    default_parameter = models.ForeignKey(DefaultParameter, null=True, on_delete=models.SET_NULL)
class ResourceParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ResourceParameter, on_delete=models.CASCADE)
class ResourceParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ResourceParameter, on_delete=models.CASCADE)

class ParticipantParameter(BaseParameter):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    default_parameter = models.ForeignKey(DefaultParameter, null=True, on_delete=models.SET_NULL)
class ParticipantParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ParticipantParameter, on_delete=models.CASCADE)
class ParticipantParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ParticipantParameter, on_delete=models.CASCADE)

class ParticipantContact(BaseModel):
    """Контакт участника проекта
    """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    tp = models.CharField(max_length = 40)
    contact = SafeTextField()

class ParticipantVote(BaseModel):
    """Предложение об участнике проекта
    """
    participant_status = models.ForeignKey(ParticipantStatus)
    voter = models.ForeignKey(Participant, related_name = 'acceptant_%(class)s_set', on_delete=models.CASCADE)
    comment = SafeTextField(null=False, default='')

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
