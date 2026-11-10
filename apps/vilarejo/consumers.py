"""
WebSocket Consumer do Vilarejo Literário

Gerencia conexões WebSocket para o chat em tempo real do vilarejo.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class VilarejoConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para o chat do Vilarejo Literário.

    Cada vilarejo tem seu próprio grupo de WebSocket.
    Apenas usuários autorizados (dono, vizinhos, moradores permanentes) podem se conectar.
    """

    async def connect(self):
        """Conexão WebSocket estabelecida."""
        self.vilarejo_id = self.scope['url_route']['kwargs']['vilarejo_id']
        self.room_group_name = f'vilarejo_{self.vilarejo_id}'
        self.user = self.scope['user']

        # Verificar se usuário está autenticado
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verificar se usuário tem permissão para acessar este vilarejo
        tem_acesso = await self.verificar_acesso()
        if not tem_acesso:
            await self.close()
            return

        # Entrar no grupo do vilarejo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Conexão WebSocket encerrada."""
        # Sair do grupo do vilarejo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def verificar_acesso(self):
        """Verifica se o usuário tem acesso ao vilarejo."""
        from .models import Vilarejo
        from .services import verificar_acesso_vilarejo

        try:
            vilarejo = Vilarejo.objects.get(id=self.vilarejo_id)
            tem_acesso, _, _ = verificar_acesso_vilarejo(self.user, vilarejo)
            return tem_acesso
        except Vilarejo.DoesNotExist:
            return False

    async def receive(self, text_data):
        """Mensagem recebida do WebSocket."""
        # WebSocket usado apenas para receber broadcasts
        # Mensagens são enviadas via HTTP POST para persistência
        pass

    async def chat_message(self, event):
        """Envia mensagem de chat para o WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def message_edited(self, event):
        """Envia notificação de mensagem editada."""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))

    async def message_deleted(self, event):
        """Envia notificação de mensagem excluída."""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))


# Função utilitária para broadcast de mensagens (usado pelas views)
async def broadcast_mensagem(vilarejo_id, mensagem_data):
    """
    Envia uma mensagem para todos os conectados ao vilarejo.

    Args:
        vilarejo_id: ID do vilarejo
        mensagem_data: Dicionário com dados da mensagem
    """
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    room_group_name = f'vilarejo_{vilarejo_id}'

    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'chat_message',
            'message': mensagem_data
        }
    )


async def broadcast_mensagem_editada(vilarejo_id, mensagem_data):
    """Broadcast de mensagem editada."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    room_group_name = f'vilarejo_{vilarejo_id}'

    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'message_edited',
            'message': mensagem_data
        }
    )


async def broadcast_mensagem_excluida(vilarejo_id, mensagem_id):
    """Broadcast de mensagem excluída."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    room_group_name = f'vilarejo_{vilarejo_id}'

    await channel_layer.group_send(
        room_group_name,
        {
            'type': 'message_deleted',
            'message_id': mensagem_id
        }
    )
