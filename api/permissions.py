from rest_framework.permissions import BasePermission
from .models import Group, GroupMembership, Game, GameParticipation


class IsGroupMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            return GroupMembership.objects.filter(group=obj, user=user).exists()

        if hasattr(obj, "group"):
            group = obj.group
            return GroupMembership.objects.filter(group=group, user=user).exists()

        return False


class IsGroupAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            group = obj
        elif hasattr(obj, "group"):
            group = obj.group
        else:
            return False

        if group.created_by_id == user.id:
            return True

        return GroupMembership.objects.filter(
            group=group,
            user=user,
            role=GroupMembership.Role.ADMIN,
        ).exists()


class IsGroupCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if isinstance(obj, Group):
            return obj.created_by_id == user.id

        if hasattr(obj, "group"):
            return obj.group.created_by_id == user.id

        return False


class IsGameCreatorOrGroupCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Game):
            return False

        user = request.user

        if obj.created_by_id == user.id:
            return True

        return obj.group.created_by_id == user.id


class IsSelfOrGameCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, GameParticipation):
            return False

        user = request.user
        game = obj.game

        if obj.player_id == user.id:
            return True

        if game.created_by_id == user.id:
            return True

        return game.group.created_by_id == user.id
