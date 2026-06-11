from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Team, Match
from .news_data import NEWS_LIST
import random

def index(request):
    teams = Team.objects.all().order_by('-points', '-rank')
    context = {
        'teams': teams,
        'news_items': NEWS_LIST[:4],  # Limit to 4 items initially
    }
    return render(request, 'dashboard/index.html', context)

def team_details(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
        matches = Match.objects.filter(Q(home_team=team) | Q(away_team=team)).order_by('-round_number')[:5]
        match_list = []
        for m in matches:
            is_home = m.home_team == team
            opponent = m.away_team.name if is_home else m.home_team.name
            res = "Н"
            res_color = "bg-[#1e2d3d] text-[#90a4ae]"
            if m.home_score is not None and m.away_score is not None:
                if (is_home and m.home_score > m.away_score) or (not is_home and m.away_score > m.home_score):
                    res = "В"
                    res_color = "bg-[#0d3d1d] text-[#4caf50]"
                elif (is_home and m.home_score < m.away_score) or (not is_home and m.away_score < m.home_score):
                    res = "П"
                    res_color = "bg-[#3d0d0d] text-[#ef5350]"
            match_list.append({
                'id': m.id,
                'opponent': opponent,
                'score': f"{m.home_score} – {m.away_score}",
                'result': res,
                'res_color': res_color
            })
        return JsonResponse({
            'name': team.name,
            'stats': {
                'played': team.played,
                'wins': team.wins,
                'points': team.points,
                'gf': team.goals_for,
                'ga': team.goals_against,
                'win_rate': round((team.wins / team.played * 100), 1) if team.played > 0 else 0
            },
            'matches': match_list
        })
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)

def match_detail(request, match_id):
    try:
        match = Match.objects.get(id=match_id)
        detailed_stats = {
            'possession': [random.randint(40, 60), 0],
            'shots': [random.randint(5, 20), random.randint(5, 15)],
            'shots_on_target': [random.randint(2, 8), random.randint(2, 6)],
            'corners': [random.randint(2, 10), random.randint(2, 8)],
            'fouls': [random.randint(5, 15), random.randint(5, 15)],
        }
        detailed_stats['possession'][1] = 100 - detailed_stats['possession'][0]
        return render(request, 'dashboard/match_detail.html', {'match': match, 'stats': detailed_stats})
    except Match.DoesNotExist:
        return render(request, '404.html', status=404)
