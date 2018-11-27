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
    
    url(r'^todo/$', views.to_do, name="todo"),
    url(r'^todo/completed/$', views.todo_completed, name="todo_complete"),
    url(r'^todo/(?P<todo_id>\d+)/$',
        views.todo_edit,
        name="todo_edit"),
    url(r'^todo/create/$', views.todo_admin_create, name="todo_create"),
    url(r'^todo/edit/(?P<todo_id>\d+)/$', views.todo_admin_edit, name="todo_admin_edit"),
    url(r'^todo/delete/(?P<todo_id>\d+)/$', views.todo_delete, name="todo_delete"),
    url(r'^todo/list/$', views.TodoAdminListView.as_view(), name="todo_list"),
    url(r'^todo/list/completed/$',
        views.TodoCompletedListView.as_view(),
        name="todo_complete_all"),

##    url(r'^add/$',
##        views.entryForm,
##        name="entryAdd"),

]
