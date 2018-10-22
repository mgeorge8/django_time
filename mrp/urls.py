from django.contrib import admin
from django.conf.urls import include, url
from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('timepiece.urls')),
    path('', RedirectView.as_view(url='/time/')),

    #authentication views
    url(r'^accounts/login/$', auth_views.LoginView.as_view(),
        name='auth_login'),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view(),
        name='auth_logout'),
    url(r'^accounts/password-change/$',
        auth_views.PasswordChangeView.as_view(),
        name='change_password'),
    url(r'^accounts/password-change/done/$',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),
    url(r'^accounts/password-reset/$',
        auth_views.PasswordResetView.as_view(),
        name='reset_password'),
    url(r'^accounts/password-reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^accounts/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    url(r'^accounts/reset/done/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),

]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
