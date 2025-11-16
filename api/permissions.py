from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.shortcuts import get_object_or_404

from .models import (
    Group,
    GroupMembership,
    Game,
    GameParticipation,
)


class IsGroupMember(BasePermission):
    """
    Permite ação apenas se o usuário é membro do grupo.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            return GroupMembership.objects.filter(group=obj, user=user).exists()

        # Em posts e jogos, obj pode ser Game/GroupRequest/GamePost...
        if hasattr(obj, "group"):
            group = getattr(obj, "group")
            return GroupMembership.objects.filter(group=group, user=user).exists()

        return False


class IsGroupAdmin(BasePermission):
    """
    Permite apenas admins daquele grupo.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # obj é um Group
        if isinstance(obj, Group):
            group = obj
        # Para GamePost / GameRequest / etc.
        elif hasattr(obj, "group"):
            group = obj.group
        else:
            return False

        return GroupMembership.objects.filter(
            group=group,
            user=user,
            role=GroupMembership.Role.ADMIN,
        ).exists()


class IsGroupCreator(BasePermission):
    """
    Permite apenas o criador do grupo.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            return obj.created_by_id == user.id

        if hasattr(obj, "group"):
            return obj.group.created_by_id == user.id

        return False


class IsGameCreatorOrGroupCreator(BasePermission):
    """
    Permite editar/excluir partida se:
    - usuário criou o jogo OU
    - usuário criou um grupo ao qual o jogo pertence
    """

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Game):
            return False

        user = request.user

        # Criador do jogo
        if obj.created_by_id == user.id:
            return True

        # Criador de algum grupo onde ele foi postado
        return Group.objects.filter(
            id__in=obj.groups.values_list("id", flat=True),
            created_by=user,
        ).exists()


class IsSelfOrGameCreator(BasePermission):
    """
    Permite editar participação se:
    - o jogador é o próprio usuário OU
    - o usuário criou o jogo OU
    - o usuário criou um grupo ao qual o jogo pertence
    """

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, GameParticipation):
            return False

        user = request.user
        game = obj.game

        # É o próprio jogador
        if obj.player_id == user.id:
            return True

        # Criador do jogo
        if game.created_by_id == user.id:
            return True

        # Criador de algum grupo do jogo
        return Group.objects.filter(
            id__in=game.groups.values_list("id", flat=True),
            created_by=user,
        ).exists()
