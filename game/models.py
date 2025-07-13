from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from account.models import Player
from game import CourtChoice, GameType


class Season(models.Model):
    name = models.CharField(max_length=255, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
    )
    min_sundays_for_rank = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return self.name


class PlayerSeasonStat(models.Model):
    """
    Stores a player's aggregated statistics for a specific season.
    This table is updated whenever a relevant game is logged.
    """
    # --- Core Relationships ---
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='season_stats'
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name='player_stats'
    )

    # --- Calculated Statistics ---
    total_games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    win_rate = models.FloatField(
        default=0.0,
        db_index=True,
    )
    rank = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    sundays_attended = models.IntegerField(
        default=0,
    )
    guest_games_played = models.IntegerField(default=0)

    # --- Additional Calculated Fields ---
    best_partner = models.ForeignKey(
        Player,
        related_name='best_partner_for',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The player with whom this player has the highest win rate."
    )
    odl_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Special rank for a One Day League event."
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('player', 'season')
        ordering = ['-win_rate', '-wins']
        indexes = [
            models.Index(fields=['player', 'season']),
        ]

    def __str__(self):
        return f"Stats for {self.player.name} in {self.season.name}"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically calculate the win_rate.
        """
        if self.total_games > 0:
            self.win_rate = (self.wins / self.total_games) * 100
        else:
            self.win_rate = 0.0
        super().save(*args, **kwargs)


class Game(models.Model):
    # --- Game Metadata ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    game_date = models.DateField(auto_now_add=True, db_index=True)
    season = models.ForeignKey(Season,
        on_delete=models.CASCADE,
        related_name="games",
    )
    court = models.CharField(
        max_length=1,
        choices=CourtChoice.CHOICES,
        default=CourtChoice.COURT_A,
    )
    game_type = models.CharField(
        max_length=10,
        choices=GameType.CHOICES,
        default=GameType.DOUBLES,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # --- Team 1 ---
    player1_team1 = models.ForeignKey(
        Player,
        related_name="game_as_player1_team1",
        on_delete=models.CASCADE,
    )
    #NOTE: only for Doubles; nullable for Singles game type
    player2_team1 = models.ForeignKey(
        Player,
        related_name="game_as_player2_team1",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    team1_is_winner = models.BooleanField()

    # --- Team 2 ---
    player1_team2 = models.ForeignKey(
        Player,
        related_name="game_as_player1_team2",
        on_delete=models.CASCADE,
    )
    #NOTE: only for Doubles; nullable for Singles game type
    player2_team2 = models.ForeignKey(
        Player,
        related_name="game_as_player2_team2",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    team2_is_winner = models.BooleanField()

    def __str__(self):
        return f"{self.get_game_type_display()} Game on {self.game_date}"

    def clean(self):
        #Rule 1: Ensure there is exactly one winner.
        if self.team1_is_winner == self.team2_is_winner:
            raise ValidationError("A game must have exactly one winning team.")

        # Rule 2: Validate players based on game type.
        if self.game_type == GameType.DOUBLES:
            if not all([
                self.player1_team1,
                self.player2_team1,
                self.player1_team2,
                self.player2_team2
            ]):
                raise ValidationError("Doubles games require four players.")
            players = {
                self.player1_team1,
                self.player2_team1,
                self.player1_team2,
                self.player2_team2,
            }
            if len(players) != 4:
                raise ValidationError(
                    "Doubles games must involve four unique players.",
                )
        elif self.game_type == GameType.SINGLES:
            if self.player2_team1 is not None or self.player2_team2 is not None:
                raise ValidationError(
                    "For singles games, only Player 1 of each team should be set.",
                )
            if self.player1_team1 == self.player1_team2:
                raise ValidationError(
                    "Singles games must involve two unique players."
                )

    def save(self, *args, **kwargs):
        """
        Override the save method to automatically run validation.
        """
        self.clean()
        super().save(*args, **kwargs)


class Queue(models.Model):
    """
    The order is determined by the 'created_on' timestamp (first-in, first-out).
    """
    # --- Queue Entry Details ---
    court = models.CharField(
        max_length=1,
        choices=CourtChoice.CHOICES,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(auto_now=True, null=True)
    game_type = models.CharField(
        max_length=10,
        choices=GameType.CHOICES,
        default=GameType.DOUBLES,
    )

    # --- Players in the Team ---
    player1 = models.ForeignKey(
        Player,
        related_name='queue_as_player1',
        on_delete=models.CASCADE
    )
    player2 = models.ForeignKey(
        Player,
        related_name='queue_as_player2',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["court", "game_type", "created_at"]
            )
        ]

    def __str__(self):
        team_name = self.player1.name
        if self.player2:
            team_name += f" & {self.player2.name}"
        return f"Team '{team_name}' waiting for Court {self.get_court_display()}"

    def clean(self):
        """
        Validation for the queue entry.
        """
        if self.game_type == GameType.DOUBLES and not self.player2:
            raise ValidationError(
                "A doubles team in the queue must have two players."
            )
        if self.game_type == GameType.SINGLES and self.player2:
            raise ValidationError(
                "A singles team in the queue must have only one player."
            )
        if self.game_type == GameType.DOUBLES and self.player1 == self.player2:
            raise ValidationError("The two players in a team must be unique.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
