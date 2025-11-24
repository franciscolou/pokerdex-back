from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Group,
    GroupMembership,
    GroupRequest,
    Game,
    GamePost,
    GameParticipation,
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = ["id", "user", "role", "joined_at"]


class GroupSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    member_count = serializers.IntegerField(read_only=True)
    post_count = serializers.IntegerField(read_only=True)
    last_post = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "created_by",
            "created_at",
            "member_count",
            "post_count",
            "last_post",
        ]
        read_only_fields = ["slug", "created_by", "created_at"]


class GroupDetailSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    memberships = GroupMembershipSerializer(many=True, read_only=True)

    is_member = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()

    recent_posts = serializers.SerializerMethodField()
    recent_games = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "created_by",
            "created_at",
            "memberships",
            "is_member",
            "is_admin",
            "is_creator",
            "recent_posts",
            "recent_games",
        ]

    def get_is_member(self, obj):
        user = self.context["request"].user
        return GroupMembership.objects.filter(group=obj, user=user).exists()

    def get_is_admin(self, obj):
        user = self.context["request"].user
        return GroupMembership.objects.filter(
            group=obj, user=user, role=GroupMembership.Role.ADMIN
        ).exists()

    def get_is_creator(self, obj):
        user = self.context["request"].user
        return obj.created_by_id == user.id

    def get_recent_posts(self, obj):
        posts = obj.posts.select_related("game", "posted_by").order_by("-posted_at")[:10]
        return GamePostSerializer(posts, many=True).data

    def get_recent_games(self, obj):
        games = Game.objects.filter(posts__group=obj).distinct().order_by("-date")[:10]
        return GameSerializer(games, many=True).data


class GroupRequestSerializer(serializers.ModelSerializer):
    requested_by = UserSerializer(read_only=True)

    class Meta:
        model = GroupRequest
        fields = ["id", "group", "requested_by", "message", "created_at"]
        read_only_fields = ["requested_by", "created_at"]


class GamePostSerializer(serializers.ModelSerializer):
    posted_by = UserSerializer(read_only=True)

    class Meta:
        model = GamePost
        fields = ["id", "game", "group", "posted_by", "posted_at"]


class GameParticipationSerializer(serializers.ModelSerializer):
    player = UserSerializer(read_only=True)
    player_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GameParticipation
        fields = [
            "id",
            "player",
            "player_id",
            "game",
            "rebuy",
            "final_balance",
            "created_at",
        ]
        read_only_fields = ["player", "game", "created_at"]

    def create(self, validated_data):
        validated_data["player_id"] = validated_data.pop("player_id")
        participation = GameParticipation.objects.create(**validated_data)
        return participation


class GroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "slug"]

class GameSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    group = GroupMiniSerializer(read_only=True)  # 👈 agora vem com slug

    participations_count = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id",
            "title",
            "date",
            "location",
            "buy_in",
            "created_by",
            "created_at",
            "group",
            "participations",
            "participations_count",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_participations_count(self, obj):
        return obj.participations.count()