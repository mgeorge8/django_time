from django.conf.urls import url

from timepiece.manager import views


urlpatterns = [
   

    # Users
    url(r'^user/settings/$',
        views.EditSettings.as_view(),
        name='edit_settings'),
    url(r'^user/$',
        views.ListUsers.as_view(),
        name='list_users'),
    url(r'^user/create/$',
        views.CreateUser,
        name='create_user'),
    url(r'^user/(?P<user_id>\d+)/$',
        views.ViewUser.as_view(),
        name='view_user'),
    url(r'^user/(?P<user_id>\d+)/edit/$',
        views.EditUser.as_view(),
        name='edit_user'),
    url(r'^user/(?P<user_id>\d+)/delete/$',
        views.DeleteUser.as_view(),
        name='delete_user'),

    url(r'^weektimesheetcsv/(?P<date>\d{4}-\d{2}-\d{2})/$',
        views.week_timesheet,
        name='timesheet_csv'),
    url(r'^weektimesheet/$',
        views.WeekTimesheet.as_view(),
        name='week_timesheet'),
    

    # User timesheets
    url(r'^user/(?P<user_id>\d+)/timesheet/$',
        views.view_user_timesheet,
        name='view_user_timesheet'),
    

    # Projects
    url(r'^project/$',
        views.ListProjects.as_view(),
        name='list_projects'),
    url(r'^project/create/$',
        views.CreateProject,
        name='create_project'),
    url(r'^project/(?P<project_id>\d+)/$',
        views.ViewProject.as_view(),
        name='view_project'),
    url(r'^project/(?P<project_id>\d+)/edit/$',
        views.EditProject.as_view(),
        name='edit_project'),
    url(r'^project/(?P<project_id>\d+)/delete/$',
        views.DeleteProject.as_view(),
        name='delete_project'),

     # Project timesheets
    url(r'^project/(?P<project_id>\d+)/timesheet/$',
        views.ProjectTimesheet.as_view(),
        name='view_project_timesheet'),

      # User-project relationships
    url(r'^relationship/create/$',
        views.CreateRelationship.as_view(),
        name='create_relationship'),
    url(r'^relationship/delete/$',
        views.DeleteRelationship.as_view(),
        name='delete_relationship'),
    
    ]     



