# ROADMAP - Vilarejo Literário

**Criado em:** 07/12/2025
**Status:** Em implementação

---

## 🚨 PROTOCOLO DE IMPLEMENTAÇÃO

> **IMPORTANTE:** Seguir SEMPRE este protocolo ao implementar cada fase:
> 1. Rodar o servidor
> 2. Testar eu mesmo
> 3. Se houver erros, corrigir
> 4. Repetir até não haver mais erros
> 5. **Somente então** pedir ao usuário para testar (com servidor já rodando)
> 6. Só continuar para próxima fase após aprovação explícita do usuário

---

## 1. Visão Geral

O **Vilarejo Literário** é uma funcionalidade social que permite aos usuários do Livre Dia conversarem de forma privada com seus vizinhos literários mais próximos. Cada usuário possui seu próprio vilarejo onde é o anfitrião, podendo receber até 9 vizinhos baseados em similaridade de gostos literários.

### Conceito
- Área visual e acolhedora com casinhas, árvores, grama e elementos de cenário
- Chat em tempo real entre vizinhos
- Sistema de moradores permanentes e banimentos
- Notificações de atividade
- Deve ser responsivo e mobile-first

---

## 2. Especificação de Requisitos

### 2.1 Arquitetura do Vilarejo

| Requisito | Decisão |
|-----------|---------|
| **Propriedade** | Cada usuário tem seu próprio vilarejo (é o anfitrião) |
| **Acesso** | Híbrido com notificação - pode visitar vilarejos de vizinhos mútuos |
| **Nome padrão** | "Vilarejo de [NOME DO USUÁRIO]" |
| **Nome personalizável** | Sim, o anfitrião pode alterar |
| **Limite de vizinhos** | 9 vizinhos calculados por similaridade |
| **Recálculo** | Ao acessar o vilarejo (lazy loading) |

### 2.2 Sistema de Chat

| Requisito | Decisão |
|-----------|---------|
| **Tipo** | Mensagens lineares (sem threads/respostas) |
| **Atualização** | Tempo real com WebSocket (Django Channels + Redis) |
| **Limite por vilarejo** | 2000 mensagens (FIFO - mais antigas são apagadas) |
| **Limite por mensagem** | 500 caracteres com contador regressivo |
| **Conteúdo permitido** | Texto puro, emojis, links (abrem em nova aba) |
| **Emojis** | Teclado + Seletor visual (emoji picker) |
| **Menções** | @usuario (apenas pessoas do vilarejo) |
| **Edição** | Autor pode editar suas mensagens |
| **Exclusão** | Autor, dono do vilarejo ou admin podem excluir |

### 2.3 Moderação

| Requisito | Decisão |
|-----------|---------|
| **Autor** | Pode editar e excluir suas próprias mensagens |
| **Dono do vilarejo** | Pode excluir (não editar) mensagens de outros |
| **Administradores (role=ADMIN)** | Podem acessar qualquer vilarejo e excluir qualquer mensagem |

### 2.4 Moradores Permanentes

| Requisito | Decisão |
|-----------|---------|
| **Conceito** | Vizinhos que nunca "se mudam", independente da similaridade |
| **Limite** | Sem limite de quantidade |
| **Elegibilidade** | Apenas quem já foi vizinho alguma vez pode ser convidado |
| **Conta nos 9?** | Não - são extras além dos 9 vizinhos |
| **Visual** | Aparecem junto da casa do anfitrião (não têm casinha própria) |
| **Reversível** | Sim, o anfitrião pode remover o status a qualquer momento |

### 2.5 Banimentos

| Requisito | Decisão |
|-----------|---------|
| **Tipo** | Mútuo - nenhum dos dois aparece no vilarejo do outro |
| **Limite** | Sem limite de banidos |
| **Mensagens do banido** | Permanecem no histórico (limite 2000 ou anfitrião apaga) |
| **Reversível** | Sim, o anfitrião pode desbanir a qualquer momento |

### 2.6 Histórico de Mudanças

| Requisito | Decisão |
|-----------|---------|
| **Mensagens de sistema** | "[USUARIO] se mudou para outro vilarejo" / "[USUARIO] se mudou para o seu vilarejo!" |
| **Local** | Seção separada chamada "Histórico do Condomínio" |
| **Não aparece no chat** | Correto, mantém o chat limpo |

### 2.7 Notificações

| Requisito | Decisão |
|-----------|---------|
| **Menção com @** | Usuário recebe notificação (categoria própria) |
| **Mensagem no seu vilarejo** | Notificação para o anfitrião |
| **Novo vizinho** | Registro no Histórico do Condomínio |

### 2.8 Visual e Design

| Requisito | Decisão |
|-----------|---------|
| **Tecnologia** | CSS/SVG dinâmico (sem imagens externas) |
| **Elementos** | Casinhas, árvores, grama, estradinhas, nuvens |
| **Variação** | Cada vilarejo visualmente único (seed do usuário) |
| **Dia/Noite** | Sol (7h-17h) ou Lua/estrelas (17h-7h) baseado no horário local |
| **Temas** | Suporte a tema claro e escuro |
| **Responsivo** | Mobile-first |
| **Paleta** | Seguir padrões do DESIGN.md |

### 2.9 Persistência de Mensagens

| Requisito | Decisão |
|-----------|---------|
| **Ex-vizinhos** | Mensagens permanecem no histórico |
| **Limite** | 2000 mensagens por vilarejo |
| **Rotação** | FIFO (First In, First Out) - mais antigas são apagadas |

---

## 3. Modelos de Dados (Proposta)

### 3.1 Vilarejo
```python
class Vilarejo(models.Model):
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vilarejo')
    nome = models.CharField(max_length=100)  # Padrão: "Vilarejo de {dono.nome}"
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
```

### 3.2 MensagemVilarejo
```python
class MensagemVilarejo(models.Model):
    vilarejo = models.ForeignKey(Vilarejo, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    conteudo = models.CharField(max_length=500)
    criado_em = models.DateTimeField(auto_now_add=True)
    editado_em = models.DateTimeField(null=True, blank=True)
```

### 3.3 MoradorPermanente
```python
class MoradorPermanente(models.Model):
    vilarejo = models.ForeignKey(Vilarejo, on_delete=models.CASCADE, related_name='moradores_permanentes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    convidado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['vilarejo', 'usuario']
```

### 3.4 BanimentoVilarejo
```python
class BanimentoVilarejo(models.Model):
    vilarejo = models.ForeignKey(Vilarejo, on_delete=models.CASCADE, related_name='banimentos')
    usuario_banido = models.ForeignKey(User, on_delete=models.CASCADE)
    banido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['vilarejo', 'usuario_banido']
```

### 3.5 HistoricoCondominio
```python
class HistoricoCondominio(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Se mudou para o vilarejo'),
        ('SAIDA', 'Se mudou para outro vilarejo'),
    ]

    vilarejo = models.ForeignKey(Vilarejo, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    data = models.DateTimeField(auto_now_add=True)
```

---

## 4. Plano de Implementação

### Fase 1: Infraestrutura Base ✅
- [x] Criar app `vilarejo` em `apps/`
- [x] Configurar Django Channels
- [x] Configurar Redis (local e produção)
- [x] Criar modelos de dados
- [x] Criar migrations
- [x] Configurar URLs e rotas WebSocket

### Fase 2: Backend - Core ✅
- [x] Implementar view do vilarejo (acesso e permissões)
- [x] Implementar recálculo de vizinhos ao acessar
- [x] Implementar CRUD de mensagens
- [x] Implementar limite de 2000 mensagens (FIFO)
- [x] Implementar sistema de menções (@usuario)
- [x] Implementar WebSocket consumer para chat em tempo real

### Fase 3: Backend - Gestão ✅
- [x] Implementar moradores permanentes (convidar/remover)
- [x] Implementar banimentos (banir/desbanir)
- [x] Implementar Histórico do Condomínio
- [x] Implementar alteração do nome do vilarejo
- [x] Implementar permissões de moderação (dono/admin)

### Fase 4: Sistema de Notificações ✅
- [x] Criar categoria de notificação para vilarejo (MENCAO_VILAREJO, MENSAGEM_VILAREJO)
- [x] Notificar ao ser mencionado com @
- [x] Notificar dono quando postam no vilarejo dele

### Fase 5: Frontend - Layout Base ✅
- [x] Criar template base do vilarejo
- [x] Implementar layout responsivo (mobile-first)
- [x] Implementar suporte a tema claro/escuro
- [x] Criar área do chat (com emoji picker e autocomplete de menções)
- [x] Criar área dos vizinhos (colapsável em mobile, com botão visitar)

### Fase 6: Frontend - Visual Dinâmico ✅
- [x] Criar casinhas em CSS/SVG
- [x] Criar árvores em CSS/SVG
- [x] Criar grama e estradinhas
- [x] Criar sol/nuvens (dia)
- [x] Criar lua/estrelas (noite)
- [x] Implementar variação por seed do usuário (cores dos telhados variam)
- [x] Implementar detecção de horário local (dia/noite)

### Fase 7: Frontend - Chat ✅
- [x] Implementar campo de entrada com contador regressivo
- [x] Implementar emoji picker
- [x] Implementar autocomplete de @menções
- [x] Implementar edição de mensagem
- [x] Implementar exclusão de mensagem
- [x] Implementar área de chat com altura fixa e barra de rolagem
- [x] Implementar conexão WebSocket para tempo real

### Fase 8: Frontend - Gestão ✅
- [x] Interface para convidar morador permanente
- [x] Interface para remover morador permanente
- [x] Interface para banir usuário
- [x] Interface para desbanir usuário
- [x] Interface para alterar nome do vilarejo
- [x] Interface do Histórico do Condomínio

### Fase 9: Integração
- [x] Conectar botão "Visitar meu Vilarejo Literário" do perfil
- [x] Implementar navegação entre vilarejos de vizinhos
- [ ] Testar fluxo completo
- [ ] Ajustes de UX

### Fase 10: Produção
- [ ] Configurar Redis no servidor
- [ ] Configurar Daphne/ASGI para WebSocket
- [ ] Deploy
- [ ] Testes em produção
- [ ] Monitoramento

---

## 5. Dependências Técnicas

### Novas bibliotecas necessárias:
- `channels` - Django Channels para WebSocket
- `channels-redis` - Backend Redis para Channels
- `daphne` - Servidor ASGI (produção)

### Configurações de servidor:
- Redis instalado e rodando
- Nginx configurado para WebSocket (upgrade de conexão)
- Supervisor/systemd para Daphne

---

## 6. Recursos Necessários

### Imagens:
- **Nenhuma** - todo visual será CSS/SVG dinâmico

### Dependências externas:
- Redis (já comum em produção Django)

---

## 7. Considerações Finais

### Pontos de atenção:
1. **Performance:** O recálculo de vizinhos pode ser custoso com muitos usuários. Considerar cache.
2. **WebSocket:** Requer configuração adicional no servidor (Daphne + Redis).
3. **Limite de mensagens:** O FIFO deve ser implementado de forma eficiente.
4. **Banimento mútuo:** Lógica deve verificar ambos os lados ao calcular vizinhos.

### Possíveis melhorias futuras:
- Reações em mensagens (curtir)
- Compartilhar textos do Livre Dia no chat
- Conquistas/badges do vilarejo
- Eventos sazonais (decoração de Natal, etc.)

---

**Aguardando aprovação para iniciar implementação.**
