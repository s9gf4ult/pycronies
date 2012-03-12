# -*- coding: utf-8 -*-

from django.db import models
from datetime import date, datetime
import uuid
import re

# Create your models here.

parameter_class_map = {}

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
        return u'{0}({1})'.format(type(self).__name__, self.uuid)

    class Meta:
        abstract = True
        ordering = ['create_date']

class BaseParameter(BaseModel):
    enum = models.BooleanField() # параметр с ограниченным набором значений
    tpclass = models.CharField(max_length=40) # тип, напримера "status"
    unique = models.IntegerField(null=True) # хак уникальности с полем tpclass либо null либо 1
    tp = models.CharField(max_length=40, default='text') # тип, для пользовательских параметров, если tpclass == 'user'
    name = SafeTextField(null=True, default=None)                  # имя параметра если tp == 'user'
    descr = SafeTextField(null=True, default=None)                 # описание если tp == 'user'

    class Meta:
        abstract = True
        ordering = ['name']

class BaseParameterVal(BaseModel):
    """Базовый класс значения параметра
    """
    PARAMETER_VALUE_STATUS=((u'voted', u'Значение предложено'),
                            (u'wasvoted', u'Значение было предложено'),
                            (u'accepted', u'Значение принято'),
                            (u'denied', u'Значение запрещено'),
                            (u'changed', u'Значение было изменено'))
    value = SafeTextField()
    caption = SafeTextField(null=True)
    dt = models.DateTimeField(null=True) # время начала действия значения
    status = models.CharField(max_length=40, choices=PARAMETER_VALUE_STATUS)
    class Meta:
        abstract = True
        ordering = ['status', 'value']

class BaseParameterVl(BaseModel):
    """Базовый класс возможных значений параметра
    """
    value = models.CharField(max_length=40)
    caption = models.TextField(null=True)
    class Meta:
        abstract = True
        ordering = ['value']

class DefaultParameter(BaseModel):
    """Предлагаемый параметр проекта или чего нибудь еще
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
    caption = models.TextField(default=u'')
    class Meta:
        unique_together = (('value', 'parameter'), )


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
    name = SafeCharField(max_length=100, default=None, db_index=True)
    descr = SafeTextField(default=u'', db_index=True)
    sharing = SafeCharField(max_length=40, choices=PROJECT_SHARING)
    ruleset = models.CharField(max_length=40, default='despot', null=False, choices=PROJECT_RULESET)
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    class Meta:
        ordering = ['name']

class Participant(BaseModel):
    """Участрник проекта
    """
    PARTICIPANT_STATUS=((u'accepted', u'Участник актинвен'),
                        (u'denied', u'Участник запрещен'),
                        (u'voted', u'Участник в процессе согласования'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    dt = models.DateTimeField(default=None, null=True) # Дата последнего входа участника
    is_initiator = models.BooleanField(default=False)
    user = models.CharField(max_length=40, null=True)   # FIXME: Это должна быть ссылка на пользюка, пока заглушка
    psid = models.CharField(max_length=40, unique=True, null=True, default=None)
    token = models.CharField(max_length=40, null=True, unique=True)
    name = SafeCharField(max_length=100, default=None, null=False)
    descr = SafeTextField(default=u'')
    class Meta:
        unique_together = ((u'name', u'project'),
                           (u'project', u'user'))
        ordering = ['name']

class BaseVote(BaseModel):
    """Базовый класс голоса
    """
    voter = models.ForeignKey(Participant, on_delete = models.CASCADE)
    comment = SafeTextField(null=False, default=u'')
    class Meta:
        abstract = True

class ParticipantParameter(BaseParameter):
    obj = models.ForeignKey(Participant, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('name', 'obj'),
                           ('obj', 'tpclass', 'unique'))

class ParticipantParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ParticipantParameter, on_delete = models.CASCADE)

class ParticipantParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ParticipantParameter, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )

class ParticipantParameterVote(BaseVote):
    parameter_val = models.ForeignKey(ParticipantParameterVal, on_delete=models.CASCADE)
    class Meta:
        unique_together = (('parameter_val', 'voter'), )

parameter_class_map[Participant] = {'param' : ParticipantParameter,
                                    'val' : ParticipantParameterVal,
                                    'vl' : ParticipantParameterVl,
                                    'vote' : ParticipantParameterVote}

class ProjectParameter(BaseParameter):
    obj = models.ForeignKey(Project, on_delete=models.CASCADE)
    default = models.ForeignKey(DefaultParameter, null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = (('name', 'obj'),
                           ('obj', 'tpclass', 'unique'))

class ProjectParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ProjectParameter, on_delete = models.CASCADE)

class ProjectParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ProjectParameter, on_delete = models.CASCADE)
    class Meta:
        unique_together = ((u'value', 'parameter'), )

class ProjectParameterVote(BaseVote):
    parameter_val = models.ForeignKey(ProjectParameterVal, on_delete = models.CASCADE)
    class Meta:
        unique_together = ((u'voter', 'parameter_val'), )

parameter_class_map[Project] = {'param' : ProjectParameter,
                                'val' : ProjectParameterVal,
                                'vl' : ProjectParameterVl,
                                'vote' : ProjectParameterVote}

class Activity(BaseModel):
    """Мероприятие
    """
    ACTIVITY_STATUS=((u'created', u'Мероприяте создано'),
                     (u'voted', u'Мероприятие в процессе согласования'),
                     (u'accepted', u'Мероприятие активно'),
                     (u'denied', u'Меропри запрещено'))
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = SafeTextField(default=None, null=False)
    descr = SafeTextField(default=u'')
    begin_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)

    class Meta:
        unique_together = (("project", "name"), )
        ordering = ['name']

class ActivityParameter(BaseParameter):
    obj = models.ForeignKey(Activity, on_delete = models.CASCADE)
    default = models.ForeignKey(DefaultParameter, null=True, on_delete = models.SET_NULL)
    class Meta:
        unique_together = (('obj', 'name'),
                           ('obj', 'tpclass', 'unique'))

class ActivityParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ActivityParameter, on_delete = models.CASCADE)

class ActivityParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ActivityParameter, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )

class ActivityParameterVote(BaseVote):
    parameter_val = models.ForeignKey(ActivityParameterVal, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter_val', 'voter'), )

parameter_class_map[Activity] = {'param' : ActivityParameter,
                                 'val' : ActivityParameterVal,
                                 'vl' : ActivityParameterVl,
                                 'vote' : ActivityParameterVote}

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
    ACTIVITY_PARTICIPANT_STATUS=((u'accepted', u'Участник актинвен'),
                                 (u'denied', u'Участник запрещен'),
                                 (u'voted', u'Участник в процессе согласования'))
    activity = models.ForeignKey(Activity, on_delete = models.CASCADE)
    participant = models.ForeignKey(Participant, on_delete = models.CASCADE)
    class Meta:
        unique_together = (("activity", "participant"), )

class ActivityParticipantParameter(BaseParameter):
    """Параметр участника мероприятия
    """
    obj = models.ForeignKey(ActivityParticipant, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('obj', 'name'),
                           ('obj', 'tpclass', 'unique'))

class ActivityParticipantParameterVal(BaseParameterVal):
    """Значение параметра участника мероприятия
    """
    parameter = models.ForeignKey(ActivityParticipantParameter, on_delete = models.CASCADE)

class ActivityParticipantParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ActivityParticipantParameter, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )

class ActivityParticipantParameterVote(BaseVote):
    parameter_val = models.ForeignKey(ActivityParticipantParameterVal, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter_val', 'voter'), )

parameter_class_map[ActivityParticipant] = {'param' : ActivityParticipantParameter,
                                            'val' : ActivityParticipantParameterVal,
                                            'vl' : ActivityParticipantParameterVl,
                                            'vote' : ActivityParticipantParameterVote}

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


class ActivityResourceParameter(BaseParameter):
    """Параметр ресурса мероприятия
    """
    activity_resource = models.ForeignKey(ActivityResource, on_delete=models.CASCADE)
    class Meta:
        unique_together = (('activity_resource', 'name'),
                           ('activity_resource', 'tpclass', 'unique'))

class ActivityResourceParameterVal(BaseParameterVal):
    """Значение параметра ресурса мероприятия
    """
    parameter = models.ForeignKey(ActivityResourceParameter, on_delete=models.CASCADE)

class ActivityResourceParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ActivityResourceParameter, on_delete=models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )

class ActivityResourceParameterVote(BaseVote):
    parameter_val = models.ForeignKey(ActivityResourceParameterVal, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter_val', 'voter'), )

parameter_class_map[ActivityResource] = {'param' : ActivityResourceParameter,
                                         'val' : ActivityResourceParameterVal,
                                         'vl' : ActivityResourceParameterVl,
                                         'vote' : ActivityResourceParameterVote}

class ParticipantResource(BaseModel):
    """Личный ресурс участника мероприятия
    """
    participant = models.ForeignKey(ActivityParticipant, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2, null=False, default=None)
    class Meta:
        unique_together = (("participant", "resource"), )

class ParticipantResourceParameter(BaseParameter):
    resource = models.ForeignKey(ParticipantResource, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('resource', 'name'),
                           ('resource', 'tpclass', 'unique'))

class ParticipantResourceParameterVal(BaseParameterVal):
    parameter = models.ForeignKey(ParticipantResourceParameter, on_delete = models.CASCADE)

class ParticipantResourceParameterVl(BaseParameterVl):
    parameter = models.ForeignKey(ParticipantResourceParameter, on_delete = models.CASCADE)
    class Meta:
        unique_together = (('parameter', 'value'), )

parameter_class_map[ParticipantResource] = {'param' : ParticipantResourceParameter,
                                            'val' : ParticipantResourceParameterVal,
                                            'vl' : ParticipantResourceParameterVl}

class ProjectRulesetDefaults(BaseModel): # соответствия свойств проекта дефолтным параметрам
    parameter = models.ForeignKey(DefaultParameter)
    ruleset = models.CharField(max_length=40, null=True, choices=Project.PROJECT_RULESET) # Если null значит для проектов с любым ruleset
    class Meta:
        unique_together = (('parameter', 'ruleset'))

class ParticipantContact(BaseModel):
    """Контакт участника проекта
    """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE)
    tp = models.CharField(max_length = 40)
    contact = SafeTextField()

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
