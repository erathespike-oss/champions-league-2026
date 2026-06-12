from django.contrib import admin
from django.urls import path
from dashboard.views import index, team_details, match_detail, get_h2h_data, simulate_match

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('api/team/<int:team_id>/', team_details, name='team_details'),
    path('api/h2h/', get_h2h_data, name='get_h2h_data'),
    path('api/simulate/', simulate_match, name='simulate_match'),
    path('match/<int:match_id>/', match_detail, name='match_detail'),
]
