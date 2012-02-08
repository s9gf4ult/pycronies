from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
                       # url(r'^$', 'pycronies.views.home', name='home'),
                       url(r'^project/create$', 'services.views.create_project_route'),
                       url(r'^project/list$', 'services.views.list_projects_route'),
                       url(r'^project/list/userid$', 'services.views.list_user_projects_route'),
                       url(r'^project/status/change', 'services.views.change_project_status_route'),
    # url(r'^pycronies/', include('pycronies.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)
