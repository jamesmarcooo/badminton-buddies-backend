"""Database models."""
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager):
    """Manager for users."""

    def create_user(
        self,
        email: str,
        password: str | None=None,
        **extra_fields,
    ) -> "User":
        """Create, save and return a new user."""
        if not email:
            raise ValueError("User must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email: str, password: str) -> "User":
        """Create and return a new superuser."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user

    def create_staff(self, email: str, password: str) -> "User":
        """Create and return a staff."""
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = False
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system."""

    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"


class Player(models.Model):
    """Player in the system."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="player_profile",
    )
    name = models.CharField(max_length=255, unique=True)
    overall_total_games = models.IntegerField(default=0)
    overall_wins = models.IntegerField(default=0)
    overall_win_rate = models.FloatField(default=0.0, db_index=True)
    overall_rank = models.IntegerField(null=True, blank=True, db_index=True)
    overall_sundays_attended = models.IntegerField(default=0)
    overall_guest_games_played = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    date_registered = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Return the player's name."""
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Save the player's data."""
        if self.overall_total_games > 0:
            self.overall_win_rate = (self.overall_wins / self.overall_total_games) * 100
        else:
            self.overall_win_rate = 0.0
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
