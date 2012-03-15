=======================
Когда статус ответа 412
=======================

Если HTTP статус ответа равен 412 (PRECONDITION_FAILED) это значит, что были переданы
не верные параметры запроса, либо не выполнилось одно из условий успешного
использования сервиса (например попытка изменить объект не принадлежаший
пользователю).

В этом случае в теле ответа будет JSON словарь к слючами:

- `code`: в этом поле целое число: одно из возможных значений для кода возврата
- `caption`: текстовое пояснение, в основном для отладки
- `error`: Это поле может быть Null, в нем содержится список с ошибками
  параметров (об этом ниже)

-------------------------
Возможные значения `code`
-------------------------

- PARAMETERS_BROKEN = 100

  Если поле `code` равно этому значению, значит были переданы не правильные
  парметры, в этом случае поле `error` будет содержать список с описаниями всех
  встреченных ошибок параметров. Формат списка описан ниже

- PROJECT_PARAMETER_ERROR = 101

  Возвращается при попытке присвоить значение параметра не находящееся в списке
  возможных значений параметра для параметра с ограниченным списком значений

- MUST_BE_INITIATOR = 102

  Для проектов с управлением "despot" возвращается это значение, если
  пользователь - не инициатор, а для совершения действия нужно чтобы был.

- WRONG_PROJECT_RULESET = 103

  При попытке выполнения действия, которое возможно только для проектов
  определенного типа управления

- DEFAULT_PARAMETER_NOT_FOUND = 104

  Типовой параметр не найден

- PROJECT_PARAMETER_ALREADY_EXISTS = 105

  При попытке создания параметра с тем же именем в том же проекте

- PROJECT_PARAMETER_NOT_FOUND = 106

  Параметр проекта не найден

- ACCESS_DENIED = 107

  При попытке выполнить действие над объектом не доступным для действия в данном
  контексте (например изменить объект проекта в котором пользователь не
  учавствует)

- PARTICIPANT_NOT_FOUND = 108

  Не найден участник проекта

- PROJECT_NOT_FOUND = 109

  Не найден проект

- PARTICIPANT_ALREADY_EXISTS = 110

  При попытке создания / изменения участника проекта с тем же именем и / или тем
  же `user_id` в том же проекте.

- PROJECT_MUST_BE_OPEN = 111

  При попытке входа в открытый проект, который таковым не является

- PROJECT_STATUS_MUST_BE_PLANNING = 112

  При попытке выполнить действие в проекте статус которого должен бля этого быть
  "planning".

- PARTICIPANT_DENIED = 113

  При попытке работы с участником, который запрещен в данном проекте / мероприятии

- ACTIVITY_NOT_FOUND = 114

  Мероприятие не найдено

- ACTIVITY_ALREADY_EXISTS = 115

  При попытке создания мероприятия с тем же именем в том же проекте

- WRONG_DATETIME_PERIOD = 116

  При указании периода времени, начало которого позднее указанного конца

- ACTIVITY_IS_NOT_ACCEPTED = 117

  При попытке выполнить действие, требующее чтобы статус мероприятия был
  "accepted".

- ACTIVITY_PARAMETER_ALREADY_EXISTS = 118

  При попытке создать параметр мероприятия с тем же именем

- ACTIVITY_PARAMETER_NOT_FOUND = 119

  Если указанный UUID не соответствует ни одному параметру мероприятия

- ACTIVITY_PARAMETER_ERROR = 120

  При попытке изменения параметра мероприятия с ограниченным набором значений на
  значение не из этого набора
  

^^^^^^^^^^^^^^^^^^^
JavaSctip копипаста
^^^^^^^^^^^^^^^^^^^

.. code-block:: js

  var PARAMETERS_BROKEN = 100;
  var PROJECT_PARAMETER_ERROR = 101;
  var MUST_BE_INITIATOR = 102;
  var WRONG_PROJECT_RULESET = 103;
  var DEFAULT_PARAMETER_NOT_FOUND = 104;
  var PROJECT_PARAMETER_ALREADY_EXISTS = 105;
  var PROJECT_PARAMETER_NOT_FOUND = 106;
  var ACCESS_DENIED = 107;
  var PARTICIPANT_NOT_FOUND = 108;
  var PROJECT_NOT_FOUND = 109;
  var PARTICIPANT_ALREADY_EXISTS = 110;
  var PROJECT_MUST_BE_OPEN = 111;
  var PROJECT_STATUS_MUST_BE_PLANNING = 112;
  var PARTICIPANT_DENIED = 113;
  var ACTIVITY_NOT_FOUND = 114;
  var ACTIVITY_ALREADY_EXISTS = 115;
  var WRONG_DATETIME_PERIOD = 116;
  var ACTIVITY_IS_NOT_ACCEPTED = 117;
  var ACTIVITY_PARAMETER_ALREADY_EXISTS = 118;
  var ACTIVITY_PARAMETER_NOT_FOUND = 119;
  var ACTIVITY_PARAMETER_ERROR = 120;

-------------------
Формат поля `error`
-------------------

Поле содержит список словарей, каждый словарь с такими ключами:

- `type`: Поле с типом ошибки, одно из возможных значений
   - `value`: Ошибка в значении, поле `code` содержит код ошибки
   - `dictionary`: Ошибка в значении словаря, поле `code` содержит ключ словаря,
     а поле `error` содержит список ошибок по этому значению
   - `list`: Ошибка в значении списка, поле `code` содержит номер элемента
     списка начиная с 0, поле `error` содержит список ошибок в этого элемента
- `code`: в зависимости от значения поля `type` содержит код ошибки значения
  либо ключ / индекс словаря / списка
- `error`: список таких же словарей как этот, содержит список всех ошибок для
  элемента в словаре или списке

Пример: возможные параметры запроса следующие:

- `status`: стрка со статусом мероприятия, может быть одно из:
   - `created`: Мероприятие создано
   - `voted`: Мероприятие предложено для добавления
   - `accepted`: Мероприятие используется в проекте
   - `denied`: Мероприятие исключено
- `values`: JSON кодированный список словарей с ключами
   - `value`: значение параметра
   - `caption`: подпись

Если мы подадим такие параметры в запрос:

- `status` = "wrong status"

То в ответ получим словарь:

.. code-block:: js

   {'code' : 100, //(Ошибка в параметре)
    'error' : [{'type' : 'dictionarry',
                'code' : 'status', //ошибка в поле status
                'error' : [{'type' : 'value', // Описание ошибки в значении
                            'code' : 7}]}]} //ANY_VALIDATION_FAILED

Что означает, что ошибка в словаре в поле `status` и значение не соответствует
одному из возможных значений

Если параметры будут такие

- `status`: 'created'
- `values`:

.. code-block:: js

 [{'value' : 'blah blah'},
  {'value' : 'blah blasdah',
   'caption' : 'you you'},
  {'value' : true}]

То в ответ получим:

.. code-block:: js

  {'code' : 100,
   'error' : [{'type' : 'dictionary',
               'code' : 'values', // Ошибка в ключе
               'error' : [{'type' : 'list',
                           'code' : 2, // Ошибка в третьем элементе списка
                           'error' : [{'type' : 'dictionary', // В элементе списка словарь и там ошибка
                                       'code' : 'value', //Ключ "value"
                                       'error' : [{'type' : 'value',
                                                   'code' : 6}]}]}]}]}  // VALUE_IS_NOT_A_STRING

Что означает что 3 элемент параметра `values` являющийся словарем, в ключе
"value" должен быть строкой.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Возможные значения поля `code` при проверке параметров
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- VALUE_IS_NOT_A_DICTIONARY = 0
- VALUE_IS_NOT_A_LIST = 1
- VALUE_IS_NOT_A_SET = 2
- VALUE_IS_NOT_AN_INT = 3
- VALUE_IS_NOT_A_FLOAT = 4
- VALUE_IS_NOT_A_BOOLEAN = 5
- VALUE_IS_NOT_A_STRING = 6
- ANY_VALIDATION_FAILED = 7

  возвращается в тех случаях, когда значение должно соответствоавть одному из
  возможных значений

- NO_ONE_VALIDATION_FAILED = 8
- EACH_VALIDATION_FAILED = 9
- REGEXP_MATCH_FAILED = 10

  Возвращается в тех случаях, когда строка должна совпадать с некоторым
  регулярным выражением. Если получен такой код ошибки, то это скорее всего
  означает, что пользователь ввел недопустимые символы

- REGEXP_SEARCH_FAILED = 11

  То же что и для REGEXP_MATCH_FAILED

- EQUAL_VALIDATION_FAILED = 12
- DATETIME_VALIDATION_FAILED = 13

  Параметр должен быть строкой, представляющей дату время в ISO формате. Если
  получен этот код ошибки, значит строка не может быть преобразована в дату время.

- LENGTH_VALIDATION_FAILED = 14

  В слечае если длинна параметра должна соответствовать определенным условиям,
  относится как к строкам так и к спискам

- JSON_VALIDATION_FAILED = 15

  Параметр должен быть правильными JSON данными, если получен этот код, значет
  прасер JSON не смог разобрать содержимое параметра

- CAN_NOT_PROCESS_VALUE = 16

  В случае если параметр должен быть строкой, которую можно обработать каким то
  образом. Например, если параметр должен быть строкой, отображающей целое
  число, но в параметре встречена строка, которую не возможно преобразовать в
  целое число однозначно (содержит пробельные символы внутри числа или другие не
  числовые символы в любом месте строки)


^^^^^^^^^^^^^^^^^^^^
JavaScript копипаста
^^^^^^^^^^^^^^^^^^^^

.. code-block:: js

 var VALUE_IS_NOT_A_DICTIONARY = 0;
 var VALUE_IS_NOT_A_LIST = 1;
 var VALUE_IS_NOT_A_SET = 2;
 var VALUE_IS_NOT_AN_INT = 3;
 var VALUE_IS_NOT_A_FLOAT = 4;
 var VALUE_IS_NOT_A_BOOLEAN = 5;
 var VALUE_IS_NOT_A_STRING = 6;
 var ANY_VALIDATION_FAILED = 7;
 var NO_ONE_VALIDATION_FAILED = 8;
 var EACH_VALIDATION_FAILED = 9;
 var REGEXP_MATCH_FAILED = 10;
 var REGEXP_SEARCH_FAILED = 11;
 var EQUAL_VALIDATION_FAILED = 12;
 var DATETIME_VALIDATION_FAILED = 13;
 var LENGTH_VALIDATION_FAILED = 14;
 var JSON_VALIDATION_FAILED = 15;
 var CAN_NOT_PROCESS_VALUE = 16;
