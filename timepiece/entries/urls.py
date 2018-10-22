from django.conf.urls import url

from timepiece.entries import views

urlpatterns = [
    url(r'^time/$',
        views.Dashboard.as_view(),
        name='dashboard'),

    # Active entry
    url(r'^entry/clock_in/$',
        views.clock_in,
        name='clock_in'),
    url(r'^entry/clock_out/$',
        views.clock_out,
        name='clock_out'),


    # Entries
    url(r'^entry/$',
        views.create_edit_entry,
        name='create_entry'),
    url(r'^time/(?P<entry_id>\d+)/edit/$',
        views.create_edit_entry,
        name='edit_entry'),
    url(r'^time/(?P<entry_id>\d+)/delete/$',
        views.delete_entry,
        name='delete_entry'),

]
