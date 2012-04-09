=======
Сервисы
=======


------------------
Работа с проектами
------------------

.. automodule:: services.views
   :members: create_project_route,
             list_projects_route,
             list_user_projects_route,
             change_project_status_route,
             create_project_parameter_route,
             create_project_parameter_from_default_route,
             list_project_parameters_route,
             change_project_parameter_route,
             conform_project_parameter_route,
             delete_project_route,

-----------------
Типовые параметры
-----------------

.. automodule:: services.views
   :members: list_default_parameters_route

-----------------------------
Работа с участниками проектов
-----------------------------

.. automodule:: services.views
   :members: invite_participant_route,
             conform_participant_vote_route,
             change_participant_route,
             list_participants_route,
             conform_participant_route,
             exclude_participant_route,

------------------
Участие в проектах
------------------

.. automodule:: services.views
   :members: enter_project_open_route,
             enter_project_invitation_route,

----------------------
Работа с мероприятиями
----------------------

.. automodule:: services.views
   :members: create_activity_route,
             public_activity_route,
             activity_delete_route,
             activity_deny_route,
             list_activities_route,
             activity_participation_route,
             activity_list_participants_route,
             conform_activity_route,
             create_activity_parameter_route,
             create_activity_parameter_from_default_route,
             list_activity_parameters_route,
             change_activity_parameter,
             conform_activity_parameter,


------------------
Работа с ресурсами
------------------

.. automodule:: services.views
   :members: create_project_resource_route,
             include_personal_resource_route,
             list_activity_resources_route,
             include_activity_resource_route,
             exclude_activity_resource_route,
             conform_activity_resource_route,
             set_resource_costs,

------------------
Параметры ресурсов
------------------

.. automodule:: services.views
   :members: create_activity_resource_parameter_route,
             create_activity_resource_parameter_from_default_route,
             list_activity_resource_parameters_route,
             change_resource_parameter_route,
             conform_resource_parameter_route,

------------------------
Согласование поставщиков
------------------------

.. automodule:: services.views
   :members: list_contractors,
             use_contractor_route,

-------------------
Отчеты и статистика
-------------------

.. automodule:: services.views
   :members: participant_statistics_route,

------------------
Функции поставщика
------------------

.. automodule:: services.views
   :members: contractor_list_project_resources_route,
             contractor_offer_resource_route,
             create_contractor_route,
             
-----------------------
Работа с пользователями
-----------------------

.. automodule:: services.views
   :members: check_user_exists_route,
             send_activation_mail_route,
             activate_account_route,
             authenticate_user_route,
