from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'google'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    # url(r'^search$', views.search),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)