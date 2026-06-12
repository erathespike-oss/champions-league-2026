from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from .models import Team, Match
from .news_data import NEWS_LIST
import random

def index(request):
    teams = Team.objects.all().order_by('-points', '-goal_difference', '-goals_for')
    context = {
        'teams': teams,
        'news_items': NEWS_LIST[:4],  # Limit to 4 items initially
    }
    return render(request, 'dashboard/index.html', context)

def team_details(request, team_id):
    try:
        team = Team.objects.get(id=team_id)
        matches = Match.objects.filter(Q(home_team=team) | Q(away_team=team)).order_by('-date_utc', '-round_number')[:5]
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
                'gd': team.goal_difference,
                'win_rate': round((team.wins / team.played * 100), 1) if team.played > 0 else 0
            },
            'matches': match_list
        })
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)

def get_h2h_data(request):
    team_a_id = request.GET.get('team_a')
    team_b_id = request.GET.get('team_b')
    
    if not team_a_id or not team_b_id:
        return JsonResponse({'error': 'Missing team IDs'}, status=400)
    
    if team_a_id == team_b_id:
        return JsonResponse({'error': 'Same team selected'}, status=400)
    
    try:
        team_a = Team.objects.get(id=team_a_id)
        team_b = Team.objects.get(id=team_b_id)
        
        # Filter matches where both teams participated
        matches = Match.objects.filter(
            (Q(home_team=team_a) & Q(away_team=team_b)) |
            (Q(home_team=team_b) & Q(away_team=team_a))
        ).order_by('-date_utc', '-round_number')
        
        if not matches.exists():
            return JsonResponse({'no_data': True})
        
        wins_a = 0
        wins_b = 0
        draws = 0
        match_list = []
        total_goals_a = 0
        total_goals_b = 0
        first_goal_a = 0
        first_goal_b = 0
        
        biggest_win_a = (0, "") # (diff, score_str)
        biggest_win_b = (0, "")
        
        home_wins_a = 0
        away_wins_a = 0
        home_wins_b = 0
        away_wins_b = 0

        for m in matches:
            if m.home_score is None or m.away_score is None:
                continue
                
            is_a_home = m.home_team == team_a
            score_a = m.home_score if is_a_home else m.away_score
            score_b = m.away_score if is_a_home else m.home_score
            
            total_goals_a += score_a
            total_goals_b += score_b
            
            res = "D"
            if score_a > score_b:
                wins_a += 1
                res = "A"
                if is_a_home: home_wins_a += 1
                else: away_wins_a += 1
                
                diff = score_a - score_b
                if diff > biggest_win_a[0]:
                    biggest_win_a = (diff, f"{score_a}-{score_b}")
            elif score_b > score_a:
                wins_b += 1
                res = "B"
                if not is_a_home: home_wins_b += 1
                else: away_wins_b += 1
                
                diff = score_b - score_a
                if diff > biggest_win_b[0]:
                    biggest_win_b = (diff, f"{score_b}-{score_a}")
            else:
                draws += 1
                
            match_list.append({
                'date': m.date_utc.strftime('%d.%m.%Y') if m.date_utc else "N/A",
                'home_team': m.home_team.name,
                'away_team': m.away_team.name,
                'score': f"{m.home_score} - {m.away_score}",
                'stage': m.stage or "Swiss Stage",
                'is_current_season': True # All data in CSV is 24/25
            })

        count = len(match_list)
        return JsonResponse({
            'team_a': {'name': team_a.name, 'logo': team_a.logo_url, 'wins': wins_a},
            'team_b': {'name': team_b.name, 'logo': team_b.logo_url, 'wins': wins_b},
            'draws': draws,
            'total_matches': count,
            'avg_goals': round((total_goals_a + total_goals_b) / count, 2) if count > 0 else 0,
            'matches': match_list,
            'stats': {
                'biggest_win_a': biggest_win_a[1],
                'biggest_win_b': biggest_win_b[1],
                'home_away_a': f"{home_wins_a}H / {away_wins_a}A",
                'home_away_b': f"{home_wins_b}H / {away_wins_b}A",
            }
        })
    except (Team.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid team selection'}, status=400)

from dataclasses import dataclass, asdict
import math

@dataclass
class SimulationResult:
    team_a: str
    team_b: str
    win_prob_a: float
    draw_prob: float
    win_prob_b: float
    predicted_score_a: int
    predicted_score_b: int
    xg_a: float
    xg_b: float
    top_scores: list # list of [score_a, score_b, prob]
    both_score_prob: float
    over_2_5_prob: float

def simulate_match(request):
    team_a_id = request.GET.get('team_a')
    team_b_id = request.GET.get('team_b')
    
    if not team_a_id or not team_b_id or team_a_id == team_b_id:
        return JsonResponse({'error': 'Invalid teams'}, status=400)
    
    try:
        team_a = Team.objects.get(id=team_a_id)
        team_b = Team.objects.get(id=team_b_id)
        
        # Calculate league averages
        all_teams = Team.objects.all()
        total_played = sum(t.played for t in all_teams)
        total_gf = sum(t.goals_for for t in all_teams)
        
        if total_played == 0:
            return JsonResponse({'error': 'No data for simulation'}, status=400)
            
        league_avg_goals = total_gf / total_played
        
        # Strengths
        def get_strength(team):
            att = (team.goals_for / team.played) / league_avg_goals if team.played > 0 else 1.0
            def_ = (team.goals_against / team.played) / league_avg_goals if team.played > 0 else 1.0
            return att, def_
            
        att_a, def_a = get_strength(team_a)
        att_b, def_b = get_strength(team_b)
        
        # xG
        xg_a = att_a * def_b * league_avg_goals
        xg_b = att_b * def_a * league_avg_goals
        
        # Poisson distribution for probabilities
        def poisson(l, k):
            return (math.pow(l, k) * math.exp(-l)) / math.factorial(k)
            
        max_goals = 10
        prob_matrix = [[0] * max_goals for _ in range(max_goals)]
        
        win_a = 0
        draw = 0
        win_b = 0
        both_score = 0
        over_2_5 = 0
        
        score_probs = []
        
        for i in range(max_goals):
            for j in range(max_goals):
                p_i = poisson(xg_a, i)
                p_j = poisson(xg_b, j)
                prob = p_i * p_j
                prob_matrix[i][j] = prob
                
                if i > j: win_a += prob
                elif i < j: win_b += prob
                else: draw += prob
                
                if i > 0 and j > 0: both_score += prob
                if i + j > 2.5: over_2_5 += prob
                
                score_probs.append({'score': f"{i}-{j}", 'prob': prob, 'a': i, 'b': j})
        
        # Sort scores by probability
        score_probs.sort(key=lambda x: x['prob'], reverse=True)
        top_scores = [[s['a'], s['b'], round(s['prob'] * 100, 1)] for s in score_probs[:5]]
        
        predicted_score = score_probs[0]
        
        # Randomization as requested (slightly vary results)
        variation = random.uniform(0.98, 1.02)
        
        result = SimulationResult(
            team_a=team_a.name,
            team_b=team_b.name,
            win_prob_a=round(win_a * 100 * variation, 1),
            draw_prob=round(draw * 100, 1), # Keep draw more stable
            win_prob_b=round(win_b * 100 * (2 - variation), 1),
            predicted_score_a=predicted_score['a'],
            predicted_score_b=predicted_score['b'],
            xg_a=round(xg_a, 2),
            xg_b=round(xg_b, 2),
            top_scores=top_scores,
            both_score_prob=round(both_score * 100, 1),
            over_2_5_prob=round(over_2_5 * 100, 1)
        )
        
        return JsonResponse(asdict(result))
        
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)

@dataclass
class PlayerLineup:
    player_id: int
    name: str
    number: int
    position: str        # GK, CB, LB, RB, CM, LW, RW, ST...
    photo_path: str      # путь к фото
    age: int
    country: str
    country_flag: str    # emoji флага или путь к изображению
    is_substitute: bool  # запасной?
    subbed_in_minute: int = None
    subbed_out_minute: int = None
    goals: list = None   # минуты голов
    yellow_cards: int = 0
    red_card: bool = False

    def __post_init__(self):
        if self.goals is None: self.goals = []

@dataclass  
class MatchLineup:
    team_name: str
    team_logo: str
    formation: str       # "4-3-3", "4-2-3-1" и т.д.
    players: list[PlayerLineup]
    substitutes: list[PlayerLineup]
    coach: str = "Unknown"

@dataclass
class MatchDetail:
    match_id: int
    home_team: str
    away_team: str
    home_logo: str
    away_logo: str
    score_home: int
    score_away: int
    score_ht_home: int   # перерыв
    score_ht_away: int
    date: str
    stage: str
    referee: str
    venue: str
    status: str          # FINISHED / LIVE / UPCOMING
    goals_timeline: list[dict]  # [{minute, team, player, is_penalty, is_own_goal}]
    stats: dict          # {possession, shots, shots_on_target, corners, fouls, ...}
    home_lineup: MatchLineup
    away_lineup: MatchLineup
    video_url: str | None
    analysis_text: str | None
    analysis_author: str | None

def get_real_lineup(team_name, logo_url):
    if "Paris Saint-Germain" in team_name:
        players = [
            PlayerLineup(1, "Джанлуиджи Доннарумма", 1, "GK", "/static/dashboard/images/players/donnarumma.jpg", 26, "Италия", "🇮🇹", False),
            PlayerLineup(2, "Ашраф Хакими", 2, "RB", "/static/dashboard/images/players/hakimi.jpg", 26, "Марокко", "🇲🇦", False, yellow_cards=1),
            PlayerLineup(3, "Маркиньос", 5, "CB", "/static/dashboard/images/players/marquinhos.jpg", 31, "Бразилия", "🇧🇷", False),
            PlayerLineup(4, "Пачо", 51, "CB", "/static/dashboard/images/players/pacho.jpg", 23, "Эквадор", "🇪🇨", False),
            PlayerLineup(5, "Нуну Мендеш", 25, "LB", "/static/dashboard/images/players/mendes.jpg", 22, "Португалия", "🇵🇹", False),
            PlayerLineup(6, "Жоау Невеш", 87, "CM", "/static/dashboard/images/players/neves.jpg", 20, "Португалия", "🇵🇹", False),
            PlayerLineup(7, "Витинья", 17, "CM", "/static/dashboard/images/players/vitinha.jpg", 24, "Португалия", "🇵🇹", False),
            PlayerLineup(8, "Фабиан Руис", 8, "CM", "/static/dashboard/images/players/ruis.jpg", 28, "Испания", "🇪🇸", False),
            PlayerLineup(9, "Дезире Дуэ", 14, "LW", "/static/dashboard/images/players/doue.jpg", 19, "Франция", "🇫🇷", False),
            PlayerLineup(10, "Усман Дембеле", 10, "ST", "/static/dashboard/images/players/dembele.jpg", 27, "Франция", "🇫🇷", False),
            PlayerLineup(11, "Хвича Кварацхелия", 7, "RW", "/static/dashboard/images/players/khvicha.jpg", 23, "Грузия", "🇬🇪", False),
        ]
        return MatchLineup(team_name, logo_url, "4-3-3", players, [], "Луис Энрике")
    
    if "Internazionale" in team_name or "Inter" in team_name:
        players = [
            PlayerLineup(12, "Янн Зоммер", 1, "GK", "/static/dashboard/images/players/sommer.jpg", 36, "Швейцария", "🇨🇭", False),
            PlayerLineup(13, "Алессандро Бастони", 95, "CB", "/static/dashboard/images/players/bastoni.jpg", 25, "Италия", "🇮🇹", False),
            PlayerLineup(14, "Франческо Ачерби", 15, "CB", "/static/dashboard/images/players/acerbi.jpg", 36, "Италия", "🇮🇹", False),
            PlayerLineup(15, "Бенжамен Павар", 28, "CB", "/static/dashboard/images/players/pavard.jpg", 28, "Франция", "🇫🇷", False),
            PlayerLineup(16, "Федерико Димарко", 32, "LWB", "/static/dashboard/images/players/dimarco.jpg", 26, "Италия", "🇮🇹", False),
            PlayerLineup(17, "Хенрих Мхитарян", 22, "CM", "/static/dashboard/images/players/mkhitaryan.jpg", 35, "Армения", "🇦🇲", False),
            PlayerLineup(18, "Хакан Чалханоглу", 20, "CDM", "/static/dashboard/images/players/calhanoglu.jpg", 30, "Турция", "🇹🇷", False, yellow_cards=1),
            PlayerLineup(19, "Николо Барелла", 23, "CM", "/static/dashboard/images/players/barella.jpg", 27, "Италия", "🇮🇹", False),
            PlayerLineup(20, "Дензел Думфрис", 2, "RWB", "/static/dashboard/images/players/dumfries.jpg", 28, "Нидерланды", "🇳🇱", False),
            PlayerLineup(21, "Лаутаро Мартинес", 10, "ST", "/static/dashboard/images/players/martinez.jpg", 27, "Аргентина", "🇦🇷", False),
            PlayerLineup(22, "Маркус Тюрам", 9, "ST", "/static/dashboard/images/players/thuram.jpg", 26, "Франция", "🇫🇷", False),
        ]
        return MatchLineup(team_name, logo_url, "3-5-2", players, [], "Симоне Индзаги")
    
    return None

def generate_mock_lineup(team_name, logo_url):
    positions = ['GK', 'LB', 'CB', 'CB', 'RB', 'CM', 'CM', 'CM', 'LW', 'ST', 'RW']
    names = ["Ederson", "Walker", "Dias", "Ake", "Rodri", "De Bruyne", "Silva", "Foden", "Haaland", "Grealish", "Alvarez", "Courtois", "Carvajal", "Militao", "Alaba", "Kroos", "Modric", "Valverde", "Vinicius", "Benzema", "Rodrygo"]
    countries = [("Brazil", "🇧🇷"), ("England", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"), ("Portugal", "🇵🇹"), ("Norway", "🇳🇴"), ("Spain", "🇪🇸"), ("France", "🇫🇷"), ("Germany", "🇩🇪")]
    
    players = []
    for i, pos in enumerate(positions):
        country = random.choice(countries)
        players.append(PlayerLineup(
            player_id=random.randint(100, 999),
            name=random.choice(names),
            number=random.randint(1, 99),
            position=pos,
            photo_path=f"/static/dashboard/images/players/p{random.randint(1, 5)}.jpg",
            age=random.randint(19, 35),
            country=country[0],
            country_flag=country[1],
            is_substitute=False
        ))
    
    subs = []
    for i in range(5):
        country = random.choice(countries)
        subs.append(PlayerLineup(
            player_id=random.randint(100, 999),
            name=random.choice(names),
            number=random.randint(1, 99),
            position="SUB",
            photo_path=f"/static/dashboard/images/players/p{random.randint(1, 5)}.jpg",
            age=random.randint(19, 35),
            country=country[0],
            country_flag=country[1],
            is_substitute=True
        ))
        
    return MatchLineup(team_name=team_name, team_logo=logo_url, formation="4-3-3", players=players, substitutes=subs)

import json

def match_detail(request, match_id):
    try:
        m = Match.objects.get(id=match_id)
        
        # Lineups
        home_lineup = get_real_lineup(m.home_team.name, m.home_team.logo_url)
        if not home_lineup:
            home_lineup = generate_mock_lineup(m.home_team.name, m.home_team.logo_url)
            
        away_lineup = get_real_lineup(m.away_team.name, m.away_team.logo_url)
        if not away_lineup:
            away_lineup = generate_mock_lineup(m.away_team.name, m.away_team.logo_url)

        # Generate goals timeline based on scores
        timeline = []
        for _ in range(m.home_score or 0):
            p = random.choice(home_lineup.players)
            min_ = random.randint(1, 90)
            timeline.append({'minute': min_, 'team': 'home', 'player': p.name})
            p.goals.append(min_)
            
        for _ in range(m.away_score or 0):
            p = random.choice(away_lineup.players)
            min_ = random.randint(1, 90)
            timeline.append({'minute': min_, 'team': 'away', 'player': p.name})
            p.goals.append(min_)
            
        timeline.sort(key=lambda x: x['minute'])

        # Serialize lineups to JSON for JS
        home_lineup_json = json.dumps(asdict(home_lineup))
        away_lineup_json = json.dumps(asdict(away_lineup))

        # Detailed Stats
        detailed_stats = {
            'Владение': [random.randint(40, 60), 0],
            'Удары всего': [random.randint(5, 20), random.randint(5, 15)],
            'В створ': [random.randint(2, 8), random.randint(2, 6)],
            'Угловые': [random.randint(2, 10), random.randint(2, 8)],
            'Фолы': [random.randint(5, 15), random.randint(5, 15)],
            'Офсайды': [random.randint(0, 5), random.randint(0, 5)],
            'Жёлтые карточки': [random.randint(0, 4), random.randint(0, 4)],
            'Красные карточки': [random.randint(0, 1), random.randint(0, 1)],
            'Сейвы': [random.randint(1, 7), random.randint(1, 7)],
        }
        detailed_stats['Владение'][1] = 100 - detailed_stats['Владение'][0]

        # Prepare video URL for embed
        embed_url = m.video_url
        if embed_url and 'watch?v=' in embed_url:
            embed_url = embed_url.replace('watch?v=', 'embed/')

        match_data = MatchDetail(
            match_id=m.id,
            home_team=m.home_team.name,
            away_team=m.away_team.name,
            home_logo=m.home_team.logo_url,
            away_logo=m.away_team.logo_url,
            score_home=m.home_score or 0,
            score_away=m.away_score or 0,
            score_ht_home=m.halftime_home_score or 0,
            score_ht_away=m.halftime_away_score or 0,
            date=m.date_utc.strftime('%d.%m.%Y %H:%M') if m.date_utc else "TBD",
            stage=m.stage or "Swiss Stage",
            referee=m.referee or "TBD",
            venue=m.venue or "European Stadium",
            status=m.status or "FINISHED",
            goals_timeline=timeline,
            stats=detailed_stats,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            video_url=embed_url,
            analysis_text=m.analysis_text or "Великолепный матч, в котором обе команды показали высокий уровень футбола. Тактическая борьба в центре поля стала решающим фактором.",
            analysis_author=m.analysis_author or "Champions Analytics",
        )

        return render(request, 'dashboard/match_detail.html', {
            'm': match_data,
            'home_lineup_json': home_lineup_json,
            'away_lineup_json': away_lineup_json
        })
    except Match.DoesNotExist:
        return render(request, '404.html', status=404)
