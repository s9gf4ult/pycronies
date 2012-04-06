from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       # url(r'^$', 'pycronies.views.home', name='home'),
                       url(r'^services/activity/create$', 'services.views.create_activity_route'),
                       url(r'^services/activity/delete$', 'services.views.activity_delete_route'),
                       url(r'^services/activity/deny$', 'services.views.activity_deny_route'), 
                       url(r'^services/activity/list$', 'services.views.list_activities_route'),
                       url(r'^services/activity/parameter/change$', 'services.views.change_activity_parameter_route'),
                       url(r'^services/activity/parameter/conform$', 'services.views.conform_activity_parameter'),
                       url(r'^services/activity/parameter/create$', 'services.views.create_activity_parameter_route'),
                       url(r'^services/activity/parameter/create/fromdefault$', 'services.views.create_activity_parameter_from_default_route'),
                       url(r'^services/activity/parameter/list$', 'services.views.list_activity_parameters_route'),
                       url(r'^services/activity/participant/list$', 'services.views.list_activity_participants_route'),
                       url(r'^services/activity/participation$', 'services.views.activity_participation_route'),
                       url(r'^services/activity/public$', 'services.views.public_activity_route'),
                       url(r'^services/activity/report$', 'services.views.activity_statistics_route'),
                       url(r'^services/activity/resource/conform$', 'services.views.conform_activity_resource_route'),
                       url(r'^services/activity/resource/exclude$', 'services.views.exclude_activity_resource_route'),
                       url(r'^services/activity/resource/include$', 'services.views.include_activity_resource_route'),
                       url(r'^services/activity/resource/list$', 'services.views.list_activity_resources_route'),
                       url(r'^services/activity/resource/parameter/change$', 'services.views.change_resource_parameter_route'),
                       url(r'^services/activity/resource/parameter/conform$', 'services.views.conform_resource_parameter_route'),
                       url(r'^services/activity/resource/parameter/create$', 'services.views.create_activity_resource_parameter_route'),
                       url(r'^services/activity/resource/parameter/create/fromdefault$', 'services.views.create_activity_resource_parameter_from_default_route'),
                       url(r'^services/activity/resource/parameter/list$', 'services.views.list_activity_resource_parameters_route'),
                       url(r'^services/contractor/create$', 'services.views.create_contractor_route'),
                       url(r'^services/contractor/list$', 'services.views.list_contractors'),
                       url(r'^services/contractor/project/resource/list$', 'services.views.contractor_list_project_resources_route'),
                       url(r'^services/contractor/resource/offer$', 'services.views.contractor_offer_resource_route'),
                       url(r'^services/parameters/list$', 'services.views.list_default_parameters_route'),
                       url(r'^services/participant/change$', 'services.views.change_participant_route'),
                       url(r'^services/participant/conform$', 'services.views.conform_participant_route'),
                       url(r'^services/participant/exclude$', 'services.views.exclude_participant_route'),
                       url(r'^services/participant/invite$', 'services.views.invite_participant_route'),
                       url(r'^services/participant/list$', 'services.views.list_participants_route'),
                       url(r'^services/participant/report$', 'services.views.participant_statistics_route'),
                       url(r'^services/participant/resource/use$', 'services.views.include_personal_resource_route'),
                       url(r'^services/participant/vote/conform$', 'services.views.conform_participant_vote_route'),
                       url(r'^services/project/conform$', 'services.views.conform_project_parameter_route'),
                       url(r'^services/project/create$', 'services.views.create_project_route'),
                       url(r'^services/project/enter/invitation$', 'services.views.enter_project_invitation_route'),
                       url(r'^services/project/enter/open$', 'services.views.enter_project_open_route'),
                       url(r'^services/project/list$', 'services.views.list_projects_route'),
                       url(r'^services/project/list/userid$', 'services.views.list_user_projects_route'),
                       url(r'^services/project/parameter/change$', 'services.views.change_project_parameter_route'),
                       url(r'^services/project/parameter/create$', 'services.views.create_project_parameter_route'),
                       url(r'^services/project/parameter/create/fromdefault$', 'services.views.create_project_parameter_from_default_route'),
                       url(r'^services/project/parameter/list$', 'services.views.list_project_parameters_route'),
                       url(r'^services/project/report$', 'services.views.project_statistics_route'),
                       url(r'^services/project/status/change$', 'services.views.change_project_status_route'),
                       url(r'^services/resource/contractor/use$', 'services.views.use_contractor_route'),
                       url(r'^services/resource/cost/change$', 'services.views.set_resource_costs_route'),
                       url(r'^services/resource/create$', 'services.views.create_project_resource_route'),
                       
    # url(r'^pycronies/', include('pycronies.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
                       url(r'^services/project/delete', 'services.views.delete_project_route'), # just for testing
)

