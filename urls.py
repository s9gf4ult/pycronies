from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       # url(r'^$', 'pycronies.views.home', name='home'),
                       url(r'^project/create$', 'services.views.create_project_route'),
                       url(r'^project/list$', 'services.views.list_projects_route'),
                       url(r'^project/conform$', 'services.views.conform_project_parameter_route'),
                       url(r'^project/list/userid$', 'services.views.list_user_projects_route'),
                       url(r'^project/status/change$', 'services.views.change_project_status_route'),
                       url(r'^project/parameter/create$', 'services.views.create_project_parameter_route'),
                       url(r'^project/parameter/create/fromdefault$', 'services.views.create_project_parameter_from_default_route'),
                       url(r'^project/parameter/change$', 'services.views.change_project_parameter_route'),
                       url(r'^project/parameter/list$', 'services.views.list_project_parameters_route'),
                       url(r'^project/enter/open', 'services.views.enter_project_open_route'),
                       url(r'^project/enter/invitation', 'services.views.enter_project_invitation_route'),
                       url(r'^parameters/list$', 'services.views.list_default_parameters_route'),

                       url(r'^participant/change$', 'services.views.change_participant_route'),
                       url(r'^participant/list$', 'services.views.list_participants_route'),
                       url(r'^participant/invite$', 'services.views.invite_participant_route'),
                       url(r'^participant/vote/conform$', 'services.views.conform_participant_vote_route'),
                       url(r'^participant/conform$', 'services.views.conform_participant_route'),
                       url(r'^participant/exclude$', 'services.views.exclude_participant_route'),
                       url(r'^participant/resource/use', 'services.views.include_personal_resource_route'),
                       url(r'^activity/create$', 'services.views.create_activity_route'),
                       url(r'^activity/delete$', 'services.views.activity_delete_route'),
                       url(r'^activity/deny$', 'services.views.activity_deny_route'), 
                       url(r'^activity/public$', 'services.views.public_activity_route'),
                       url(r'^activity/list$', 'services.views.list_activities_route'),
                       url(r'^activity/participation$', 'services.views.activity_participation_route'),
                       url(r'^activity/participant/list$', 'services.views.activity_list_participants_route'),
                       url(r'^activity/parameter/create$', 'services.views.create_activity_parameter_route'),
                       url(r'^activity/parameter/create/fromdefault$', 'services.views.create_activity_parameter_from_default_route'),
                       url(r'^activity/parameter/list$', 'services.views.list_activity_parameters_route'),
                       url(r'^activity/parameter/change$', 'services.views.change_activity_parameter_route'),
                       url(r'^activity/parameter/conform$', 'services.views.conform_activity_parameter'),
                       url(r'^activity/resource/include$', 'services.views.include_activity_resource_route'),
                       url(r'^activity/resource/exclude$', 'services.views.exclude_activity_resource_route'),
                       url(r'^activity/resource/conform$', 'services.views.conform_activity_resource_route'),
                       url(r'^activity/resource/list$', 'services.views.list_activity_resources_route'),
                       url(r'^activity/resource/parameter/create', 'services.views.create_activity_resource_parameter_route'),
                       url(r'^activity/resource/parameter/create/from_default', 'services.views.create_activity_resource_parameter_from_default_route'),
                       url(r'^activity/resource/parameter/list', 'services.views.list_activity_resource_parameters_route'),
                       url(r'^activity/resource/parameter/change', 'services.views.change_resource_parameter_route'),
                       url(r'^activity/resource/parameter/conform', 'services.views.conform_resource_parameter_route'),
                       url(r'^resource/create$', 'services.views.create_project_resource_route'),
                       
    # url(r'^pycronies/', include('pycronies.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
                       url(r'^project/delete', 'services.views.delete_project_route'), # just for testing
)

