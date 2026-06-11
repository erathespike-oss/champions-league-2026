import csv
from typing import Set
from django.db import transaction
from dashboard.models import Team, Match

class KaggleETL:
    """Пайплайн для импорта данных UCL 24/25 из CSV."""

    def run_pipeline(self, file_path: str) -> None:
        print(f"Starting ETL from {file_path}...")
        
        ucl_rows = []
        team_names: Set[str] = set()

        # 1. Чтение и фильтрация
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['competition_name'] == 'UEFA Champions League':
                    ucl_rows.append(row)
                    team_names.add(row['home_team'])
                    team_names.add(row['away_team'])

        # 2. Создание команд
        with transaction.atomic():
            # Очистка старых данных для чистого импорта
            Match.objects.all().delete()
            Team.objects.all().delete()
            
            teams_dict = {}
            for name in team_names:
                # Генерируем путь к лого на основе названия команды
                safe_name = name.lower().replace(" ", "_").replace(".", "")
                logo_path = f"/static/dashboard/images/logos/{safe_name}.png"
                team = Team.objects.create(name=name, logo_url=logo_path)
                teams_dict[name] = team

            # 3. Создание матчей и обновление статистики
            matches_to_create = []
            for row in ucl_rows:
                home_team = teams_dict[row['home_team']]
                away_team = teams_dict[row['away_team']]
                
                h_score = int(row['fulltime_home']) if row['fulltime_home'] else None
                a_score = int(row['fulltime_away']) if row['fulltime_away'] else None
                
                match = Match(
                    home_team=home_team,
                    away_team=away_team,
                    home_score=h_score,
                    away_score=a_score,
                    round_number=int(row.get('matchday', 1))
                )
                matches_to_create.append(match)

                # Обновляем статистику команд, если матч сыгран
                if h_score is not None and a_score is not None:
                    home_team.played += 1
                    away_team.played += 1
                    home_team.goals_for += h_score
                    home_team.goals_against += a_score
                    away_team.goals_for += a_score
                    away_team.goals_against += h_score

                    if h_score > a_score:
                        home_team.wins += 1
                        home_team.points += 3
                        away_team.losses += 1
                    elif h_score < a_score:
                        away_team.wins += 1
                        away_team.points += 3
                        home_team.losses += 1
                    else:
                        home_team.draws += 1
                        away_team.draws += 1
                        home_team.points += 1
                        away_team.points += 1

            Match.objects.bulk_create(matches_to_create)
            
            # Сохраняем обновленную статистику команд
            for team in teams_dict.values():
                team.save()

        print(f"Imported {len(team_names)} teams and {len(matches_to_create)} matches.")
