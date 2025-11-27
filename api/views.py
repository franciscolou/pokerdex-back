import secrets
from .models import PasswordResetToken, User
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count, Max, Q

from .models import (
    Group, GroupMembership, GroupRequest,
    Game, GamePost, GameParticipation
)
from .serializers import (
    GroupSerializer, GroupDetailSerializer,
    GroupRequestSerializer,
    GameSerializer,
    GameParticipationSerializer,
)
from .permissions import (
    IsGroupAdmin, IsGroupCreator,
    IsGameCreatorOrGroupCreator,
    IsSelfOrGameCreator,
    IsGroupMember,
)

@api_view(["POST"])
def request_password_reset(request):
    identifier = request.data.get("email")  # ou email/cpf/etc
    user = User.objects.filter(email=identifier).first()

    if not user:
        return Response({"detail": "Usuário não encontrado"}, status=404)

    PasswordResetToken.objects.filter(user=user).delete()  # remove tokens antigos

    token = secrets.token_hex(32)
    PasswordResetToken.objects.create(user=user, token=token)

    return Response({
        "detail": "Token gerado com sucesso!",
        "token": token  # ⚠️ SEM E-MAIL → aparece aqui no terminal/postman
    })

@api_view(["POST"])
def confirm_password_reset(request):
    token = request.data.get("token")
    password = request.data.get("password")

    reset = PasswordResetToken.objects.filter(token=token).first()
    if not reset or not reset.is_valid():
        return Response({"detail": "Token inválido ou expirado"}, status=400)

    user = reset.user
    user.set_password(password)
    user.save()
    reset.delete()

    return Response({"detail": "Senha redefinida com sucesso!"})

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().select_related("created_by")
    serializer_class = GroupSerializer
    lookup_field = "slug"

    def get_permissions(self):
        if self.action in ["create", "list", "retrieve"]:
            return [IsAuthenticated()]

        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsGroupCreator()]

        if self.action in ["promote", "demote", "remove_member"]:
            return [IsAuthenticated(), IsGroupAdmin()]

        if self.action in ["leave", "join_request"]:
            return [IsAuthenticated()]

        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        user = request.user
        search_term = request.query_params.get("search", "").strip()

        base_qs = Group.objects.all().select_related("created_by")

        if search_term:
            base_qs = base_qs.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        my_groups = (
            base_qs.filter(memberships__user=user)
            .annotate(
                member_count=Count("memberships", distinct=True),
                post_count=Count("posts", distinct=True),
                last_post=Max("posts__posted_at"),
            ).distinct()
        )

        requested_groups = base_qs.filter(
            join_requests__requested_by=user
        ).distinct()

        other_groups = (
            base_qs.exclude(memberships__user=user)
            .exclude(join_requests__requested_by=user)
            .annotate(
                member_count=Count("memberships", distinct=True),
                post_count=Count("posts", distinct=True),
                last_post=Max("posts__posted_at"),
            ).distinct()
        )

        return Response({
            "myGroups": GroupSerializer(my_groups, many=True, context={"request": request}).data,
            "requestedGroups": GroupSerializer(requested_groups, many=True, context={"request": request}).data,
            "otherGroups": GroupSerializer(other_groups, many=True, context={"request": request}).data,
        })

    def perform_create(self, serializer):
        with transaction.atomic():
            group = serializer.save(created_by=self.request.user)
            GroupMembership.objects.create(
                user=self.request.user,
                group=group,
                role=GroupMembership.Role.OWNER
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def join_request(self, request, slug=None):
        group = self.get_object()

        if GroupMembership.objects.filter(group=group, user=request.user).exists():
            return Response({"detail": "Você já é membro."}, status=400)

        if GroupRequest.objects.filter(group=group, requested_by=request.user).exists():
            return Response({"detail": "Pedido já enviado."}, status=400)

        GroupRequest.objects.create(group=group, requested_by=request.user)
        return Response({"detail": "Pedido enviado."})

    @action(detail=True, methods=["post"], url_path="promote/(?P<user_id>[^/.]+)")
    def promote(self, request, slug=None, user_id=None):
        group = self.get_object()
        target_user = get_object_or_404(GroupMembership, group=group, user_id=user_id)

        if target_user.user == group.created_by:
            return Response({"detail": "O criador já é admin."}, status=400)

        target_user.role = GroupMembership.Role.ADMIN
        target_user.save()

        return Response({"detail": "Usuário promovido."})

    @action(detail=True, methods=["post"], url_path="demote/(?P<user_id>[^/.]+)")
    def demote(self, request, slug=None, user_id=None):
        group = self.get_object()
        target_user = get_object_or_404(GroupMembership, group=group, user_id=user_id)

        if target_user.user == group.created_by:
            return Response({"detail": "Não pode rebaixar o criador."}, status=400)

        target_user.role = GroupMembership.Role.MEMBER
        target_user.save()

        return Response({"detail": "Usuário rebaixado."})

    @action(detail=True, methods=["post"], url_path="remove/(?P<user_id>[^/.]+)")
    def remove_member(self, request, slug=None, user_id=None):
        group = self.get_object()

        if int(user_id) == group.created_by_id:
            return Response({"detail": "Não pode remover o criador."}, status=400)

        deleted = GroupMembership.objects.filter(
            group=group, user_id=user_id
        ).delete()

        return Response({
            "detail": "Membro removido." if deleted else "Não era membro."
        })

    @action(detail=True, methods=["post"])
    def leave(self, request, slug=None):
        group = self.get_object()
        user = request.user

        if user == group.created_by:
            new_owner = (
                GroupMembership.objects
                .filter(group=group, role=GroupMembership.Role.ADMIN)
                .exclude(user=user)
                .order_by("joined_at")
                .first()
            )

            if not new_owner:
                new_owner = (
                    GroupMembership.objects
                    .filter(group=group, role=GroupMembership.Role.MEMBER)
                    .exclude(user=user)
                    .order_by("joined_at")
                    .first()
                )

            if new_owner:
                group.created_by = new_owner.user
                group.save()
                new_owner.role = GroupMembership.Role.ADMIN
                new_owner.save()
            else:
                group.delete()
                return Response({"detail": "Grupo deletado."})

        GroupMembership.objects.filter(group=group, user=user).delete()
        return Response({"detail": "Você saiu do grupo."})


    def retrieve(self, request, *args, **kwargs):
        group = self.get_object()
        serializer = GroupDetailSerializer(group, context={"request": request})
        return Response(serializer.data)


class GroupRequestViewSet(viewsets.ModelViewSet):
    queryset = GroupRequest.objects.all().select_related("group", "requested_by")
    serializer_class = GroupRequestSerializer

    def get_permissions(self):
        if self.action in ["list", "create", "retrieve"]:
            return [IsAuthenticated()]

        if self.action in ["destroy", "accept"]:
            return [IsAuthenticated(), IsGroupAdmin()]

        return [IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        join_request = self.get_object()
        group = join_request.group

        GroupMembership.objects.get_or_create(
            user=join_request.requested_by,
            group=group,
            defaults={"role": GroupMembership.Role.MEMBER},
        )
        join_request.delete()

        return Response({"detail": "Pedido aceito."})



class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all().select_related("created_by")
    serializer_class = GameSerializer

    def get_permissions(self):
        if self.action in ["retrieve"]:
            return [IsAuthenticated(), IsGroupMember()]

        if self.action == "create":
            return [IsAuthenticated()]

        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsGameCreatorOrGroupCreator()]

        if self.action in ["add_participation", "remove_participation"]:
            return [IsAuthenticated(), IsGameCreatorOrGroupCreator()]

        return [IsAuthenticated()]


    def perform_create(self, serializer):
        group_id = self.request.data.get("group_id")

        if not GroupMembership.objects.filter(
            group_id=group_id, user=self.request.user
        ).exists():
            raise PermissionDenied("Você não é membro desse grupo.")

        game = serializer.save(created_by=self.request.user)

        GamePost.objects.get_or_create(
            game=game,
            group_id=group_id,
            defaults={"posted_by": self.request.user}
        )


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = GameSerializer(instance, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_participation(self, request, pk=None):
        game = self.get_object()

        player_id = request.data.get("player_id")
        if not player_id:
            return Response({"detail": "player_id é obrigatório"}, status=400)

        rebuy = request.data.get("rebuy", 0)
        final_balance = request.data.get("final_balance")

        with transaction.atomic():
            participation, created = GameParticipation.objects.update_or_create(
                game=game,
                player_id=player_id,
                defaults={
                    "rebuy": rebuy,
                    "final_balance": final_balance,
                }
            )

        return Response({
            "id": participation.id,
            "created": created,
            "message": "Criado com sucesso." if created else "Atualizado com sucesso."
        })

    @action(detail=True, methods=["post"])
    def remove_participation(self, request, pk=None):
        player_id = request.data.get("player_id")

        if not player_id:
            return Response({"detail": "player_id é obrigatório"}, status=400)

        deleted, _ = GameParticipation.objects.filter(
            game_id=pk, player_id=player_id
        ).delete()

        return Response({
            "removed": deleted > 0,
            "message": "Removido com sucesso." if deleted else "Nenhuma participação encontrada."
        })
    @action(detail=True, methods=["delete"], permission_classes=[IsAuthenticated, IsGameCreatorOrGroupCreator])
    def delete(self, request, pk=None):
        game = self.get_object()

        with transaction.atomic():
            GamePost.objects.filter(game=game).delete()
            GameParticipation.objects.filter(game=game).delete()
            game.delete()

        return Response({"detail": "Jogo deletado."})


class GameParticipationViewSet(viewsets.ModelViewSet):
    queryset = GameParticipation.objects.all()
    serializer_class = GameParticipationSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), IsGroupMember()]

        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsSelfOrGameCreator()]

        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()
