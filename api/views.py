from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Count, Max

from .models import (
    Group, GroupMembership, GroupRequest,
    Game, GamePost, GameParticipation
)
from .serializers import (
    GroupSerializer, GroupDetailSerializer,
    GroupMembershipSerializer,
    GroupRequestSerializer,
    GameSerializer,
    GameParticipationSerializer,
)
from .permissions import (
    IsGroupAdmin, IsGroupCreator,
    IsGameCreatorOrGroupCreator,
    IsSelfOrGameCreator,
)
from django.db.models import Count, Max


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().select_related("created_by")
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = "slug"
    
    def list(self, request, *args, **kwargs):
        user = request.user

        
        my_groups = (
            Group.objects.filter(memberships__user=user)
            .annotate(
                member_count=Count("memberships", distinct=True),
                post_count=Count("posts", distinct=True),
                last_post=Max("posts__posted_at")
            )
            .distinct()
        )

        requested_groups = Group.objects.filter(
            join_requests__requested_by=user
        )
        
        other_groups = (
            Group.objects.exclude(memberships__user=user)
            .exclude(join_requests__requested_by=user)
            .annotate(
            member_count=Count("memberships", distinct=True),
            post_count=Count("posts", distinct=True),
            last_post=Max("posts__posted_at")
            )
            .distinct()
        )
 
        my_data = GroupSerializer(my_groups, many=True, context={"request": request}).data
        requested_data = GroupSerializer(requested_groups, many=True, context={"request": request}).data
        other_data = GroupSerializer(other_groups, many=True, context={"request": request}).data

        return Response({
            "myGroups": my_data,
            "requestedGroups": requested_data,
            "otherGroups": other_data,
        })

    
    def perform_create(self, serializer):
        """Criar grupo + adicionar criador como admin"""
        with transaction.atomic():
            group = serializer.save(created_by=self.request.user)
            GroupMembership.objects.create(
                user=self.request.user,
                group=group,
                role=GroupMembership.Role.OWNER
            )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def join_request(self, request, slug=None):
        group = self.get_object()

        if GroupMembership.objects.filter(group=group, user=request.user).exists():
            return Response({"detail": "Você já é membro."}, status=400)

        if GroupRequest.objects.filter(group=group, requested_by=request.user).exists():
            return Response({"detail": "Pedido já enviado."}, status=400)

        GroupRequest.objects.create(group=group, requested_by=request.user)
        return Response({"detail": "Pedido enviado."})


    @action(
        detail=True,
        methods=["post"],
        url_path="promote/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsGroupAdmin]
    )
    def promote(self, request, slug=None, user_id=None):
        group = self.get_object()
        target_user = get_object_or_404(GroupMembership, group=group, user_id=user_id)

        if target_user.user == group.created_by:
            return Response({"detail": "O criador já é admin."}, status=400)

        target_user.role = GroupMembership.Role.ADMIN
        target_user.save()
        return Response({"detail": "Usuário promovido."})

    @action(
        detail=True,
        methods=["post"],
        url_path="demote/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsGroupAdmin]
    )
    def demote(self, request, slug=None, user_id=None):
        group = self.get_object()
        target_user = get_object_or_404(GroupMembership, group=group, user_id=user_id)

        if target_user.user == group.created_by:
            return Response({"detail": "Não pode rebaixar o criador."}, status=400)

        target_user.role = GroupMembership.Role.MEMBER
        target_user.save()
        return Response({"detail": "Usuário rebaixado."})

    @action(
        detail=True,
        methods=["post"],
        url_path="remove/(?P<user_id>[^/.]+)",
        permission_classes=[IsAuthenticated, IsGroupAdmin]
    )
    def remove_member(self, request, slug=None, user_id=None):
        group = self.get_object()

        if int(user_id) == group.created_by_id:
            return Response({"detail": "Não pode remover o criador."}, status=400)

        deleted = GroupMembership.objects.filter(
            group=group, user_id=user_id
        ).delete()

        return Response({"detail": "Membro removido." if deleted else "Não era membro."})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated]
    )
    def leave(self, request, slug=None):
        """Lógica completa para transferência de criador e saída."""
        group = self.get_object()
        user = request.user

        if user == group.created_by:       
            new_admin = (
                GroupMembership.objects
                .filter(group=group)
                .exclude(user=user)
                .order_by("joined_at")
                .first()
            )

            if new_admin:
                group.created_by = new_admin.user
                group.save()
                new_admin.role = GroupMembership.Role.ADMIN
                new_admin.save()
            else:
                group.delete()
                return Response({"detail": "Grupo deletado."})

        GroupMembership.objects.filter(group=group, user=user).delete()

        return Response({"detail": "Você saiu do grupo."})

    def retrieve(self, request, *args, **kwargs):
        """Retorna detalhes mais completos."""
        group = self.get_object()
        serializer = GroupDetailSerializer(group, context={"request": request})
        return Response(serializer.data)


class GroupRequestViewSet(viewsets.ModelViewSet):
    queryset = GroupRequest.objects.all().select_related("group", "requested_by")
    serializer_class = GroupRequestSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        """Rejeitar pedido"""
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsGroupAdmin]
    )
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
    permission_classes = [IsAuthenticated]


    def retrieve(self, request, *args, **kwargs):
        self.get_serializer_context()
        instance = self.get_object()
        serializer = GameSerializer(
            instance=instance, 
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        game = serializer.save(created_by=self.request.user)
        group_id = self.request.data.get("group_id")
        GamePost.objects.get_or_create(
            game=game,
            group_id=group_id,
            defaults={"posted_by": self.request.user}
        )

    @action(detail=True, methods=["post"])
    def add_participation(self, request, pk=None):
        """
        ADD ou EDITAR uma participation.
        Se já houver participation para esse player, apenas atualiza.
        """
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
        """
        Remover participação de um player.
        """
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


class GameParticipationViewSet(viewsets.ModelViewSet):
    queryset = GameParticipation.objects.all()
    serializer_class = GameParticipationSerializer
    permission_classes = [IsAuthenticated, IsSelfOrGameCreator]

    def perform_create(self, serializer):
        serializer.save()
