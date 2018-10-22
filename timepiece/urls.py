from django.conf.urls import include, url
from django.urls import reverse_lazy
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

urlpatterns = [
    # Redirect the base URL to the dashboard.
    url(r'^$', RedirectView.as_view(url=reverse_lazy('dashboard'), permanent=False)),

    url('', include('timepiece.manager.urls')),
    url('', include('timepiece.entries.urls')),
    
    url(r'^docs/usersguide/$', TemplateView.as_view(template_name='UsersGuide.txt'), name="usersguide"),
    url(r'^docs/usersguideadmin/$', TemplateView.as_view(template_name='UsersGuideAdmin.txt'), name="usersguideadmin"),
]

