from django.contrib import admin
from django.urls import path
from dashboard.views import index, team_details, match_detail

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('api/team/<int:team_id>/', team_details, name='team_details'),
    path('match/<int:match_id>/', match_detail, name='match_detail'),
]
