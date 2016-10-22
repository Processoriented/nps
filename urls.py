from django.conf.urls import url

from . import views


app_name = 'maxed'
urlpatterns = [
    url(r'^$', views.index, name='index'),
]