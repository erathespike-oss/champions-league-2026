from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo_url = models.CharField(max_length=500, null=True, blank=True)
    rank = models.IntegerField(default=0)
    played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Match(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    halftime_home_score = models.IntegerField(null=True, blank=True)
    halftime_away_score = models.IntegerField(null=True, blank=True)
    round_number = models.IntegerField()
    stage = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    date_utc = models.DateTimeField(null=True, blank=True)
    referee = models.CharField(max_length=200, null=True, blank=True)
    venue = models.CharField(max_length=200, null=True, blank=True)
    video_url = models.URLField(max_length=500, null=True, blank=True)
    analysis_text = models.TextField(null=True, blank=True)
    analysis_author = models.CharField(max_length=100, null=True, blank=True)

    @property
    def is_played(self) -> bool:
        return self.home_score is not None and self.away_score is not None

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} (R{self.round_number})"
