"""
Rotas WebSocket do Vilarejo Literário
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/vilarejo/(?P<vilarejo_id>\d+)/$', consumers.VilarejoConsumer.as_asgi()),
]
