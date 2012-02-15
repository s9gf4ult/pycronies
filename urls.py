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
                       url(r'^project/parameter/list$', 'services.views.list_project_parameters_route'),
                       url(r'^parameters/list$', 'services.views.list_default_parameters_route'),

                       url(r'^participant/change$', 'services.views.change_participant_route'),
                       url(r'^participant/list$', 'services.views.list_participants_route'),
                       url(r'^participant/invite$', 'services.views.invite_participant_route'),
    # url(r'^pycronies/', include('pycronies.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
                       url(r'^project/delete', 'services.views.delete_project_route'), # just for testing
)
