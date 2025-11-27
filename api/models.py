from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class User(AbstractUser):
    email = models.EmailField(unique=True)


class Group(models.Model):
    """
    Um grupo onde partidas podem ser postadas.
    Todo usuário pode criar novos grupos. O criador vira admin automaticamente.
    """
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="groups_created",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            candidate = base
            i = 1
            while Group.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}-{i}"
            self.slug = candidate
        super().save(*args, **kwargs)


class GroupMembership(models.Model):
    """
    Associação entre usuário e grupo. 'role' define admin ou membro.
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="group_memberships"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "group")
        indexes = [
            models.Index(fields=["group", "user"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.group} ({self.role})"


class GroupInvite(models.Model):
    """
    Convite para participar de um grupo.
    Pode ser enviado por email ou por user id. Ao aceitar vira membership.
    """
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="invites"
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="invites_sent"
    )
    email = models.EmailField(blank=True)
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="invites_received"
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["group"]),
            models.Index(fields=["token"]),
        ]

    def __str__(self):
        target = self.invited_user or self.email or "invitee"
        return f"Invite({target}) -> {self.group}"


class GroupRequest(models.Model):
    """
    Pedido de um usuário para entrar em um grupo.
    Pode ser aceito ou rejeitado por um admin.
    """
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="join_requests"
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="group_requests"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("group", "requested_by")
        indexes = [
            models.Index(fields=["group"]),
            models.Index(fields=["requested_by"]),
        ]

    def __str__(self):
        return f"Request({self.requested_by} -> {self.group})"


class Game(models.Model):
    """
    Uma partida de poker. Pode ser postada em 1+ grupos.
    """
    title = models.CharField("Nome da partida", max_length=140, blank=True)
    description = models.TextField("Descrição", blank=True)
    date = models.DateField("Data", default=timezone.localdate)
    location = models.CharField("Local", max_length=180, blank=True)
    buy_in = models.DecimalField(
        "Cacife (buy-in)",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="games_created"
    )
    created_at = models.DateTimeField(default=timezone.now)

    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="games"
    )

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        label = self.title or f"Partida em {self.date.strftime('%d/%m/%Y')}"
        return f"{label}"


class GamePost(models.Model):
    """
    Relação explícita da partida com um grupo, incluindo quem postou e quando.
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    posted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="game_posts"
    )
    posted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("game", "group")
        indexes = [
            models.Index(fields=["group", "game"]),
        ]

    def __str__(self):
        return f"{self.game} @ {self.group}"


class GameParticipation(models.Model):
    """
    Participação de um jogador em uma partida.
    'final_balance' = resultado líquido (pode ser negativo).
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="participations"
    )
    player = models.ForeignKey(
        User,
        verbose_name="Jogador",
        on_delete=models.PROTECT,
        related_name="game_participations"
    )
    rebuy = models.DecimalField(
        max_digits=10,
        verbose_name="Rebuy",
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        null=True,
    )
    final_balance = models.DecimalField(
        max_digits=10,
        verbose_name="Stack final",
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("game", "player")
        indexes = [
            models.Index(fields=["game"]),
            models.Index(fields=["player"]),
        ]

    def __str__(self):
        return f"{self.player} in {self.game} -> {self.final_balance}"
