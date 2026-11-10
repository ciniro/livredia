"""
Comando de management para popular o banco de dados com dados fictícios
para a FASE 2 do projeto LIVRE DIA.

Uso: python manage.py populate_fase2
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random

from apps.textos.models import Tag, Texto, Visualizacao
from apps.comentarios.models import Comentario
from apps.core.models import PaginaEstatica

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados fictícios para a FASE 2'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n🚀 Iniciando população do banco de dados...\n'))

        # 1. Criar página estática da home
        self.criar_pagina_home()

        # 2. Criar autores
        autores = self.criar_autores()

        # 3. Criar tags
        tags = self.criar_tags()

        # 4. Criar textos
        textos = self.criar_textos(autores, tags)

        # 5. Criar visualizações
        self.criar_visualizacoes(textos)

        # 6. Criar alguns leitores
        leitores = self.criar_leitores()

        # 7. Criar comentários
        self.criar_comentarios(textos, autores, leitores)

        self.stdout.write(self.style.SUCCESS('\n✅ População concluída com sucesso!\n'))
        self.exibir_resumo()

    def criar_pagina_home(self):
        """Cria a página estática do bloco hero da home"""
        self.stdout.write('📄 Criando página estática da home...')

        conteudo = """LIVRE DIA é uma plataforma de curadoria de conteúdo 100% escrito por humanos,
        conectando autores verificados a leitores que valorizam a autenticidade e a profundidade
        da escrita genuína. Em um mundo saturado por IA, somos um oásis de vozes humanas autênticas."""

        pagina, created = PaginaEstatica.objects.get_or_create(
            slug='home-proposito',
            defaults={
                'titulo': 'Um Oásis de Conteúdo Humano.',
                'conteudo': conteudo
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Página criada'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Página já existia'))

    def criar_autores(self):
        """Cria autores fictícios"""
        self.stdout.write('\n👤 Criando autores...')

        autores_data = [
            {
                'username': 'clarice_lispector',
                'email': 'clarice@livredia.com',
                'first_name': 'Clarice',
                'last_name': 'Lispector',
                'bio': 'Exploradora da alma humana, suas crônicas revelam o extraordinário no cotidiano.',
                'cidade': 'Rio de Janeiro',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'carlos_drummond',
                'email': 'drummond@livredia.com',
                'first_name': 'Carlos',
                'last_name': 'Drummond de Andrade',
                'bio': 'Poeta do tempo e da memória, seus versos atravessam gerações com ironia e melancolia.',
                'cidade': 'Itabira',
                'pais': 'Brasil',
                'pseudonimo': 'C. Drummond',
            },
            {
                'username': 'cecilia_meireles',
                'email': 'cecilia@livredia.com',
                'first_name': 'Cecília',
                'last_name': 'Meireles',
                'bio': 'Poetisa da delicadeza e da filosofia, seus poemas são janelas para o mistério da existência.',
                'cidade': 'Rio de Janeiro',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'fernando_pessoa',
                'email': 'pessoa@livredia.com',
                'first_name': 'Fernando',
                'last_name': 'Pessoa',
                'bio': 'Mestre dos heterônimos, poeta da multiplicidade e da busca incessante pelo sentido.',
                'cidade': 'Lisboa',
                'pais': 'Portugal',
                'pseudonimo': 'Álvaro de Campos',
            },
            {
                'username': 'lygia_telles',
                'email': 'lygia@livredia.com',
                'first_name': 'Lygia',
                'last_name': 'Fagundes Telles',
                'bio': 'Contista e romancista, suas narrativas exploram o inconsciente e os dilemas contemporâneos.',
                'cidade': 'São Paulo',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'mario_quintana',
                'email': 'quintana@livredia.com',
                'first_name': 'Mário',
                'last_name': 'Quintana',
                'bio': 'O poeta das coisas simples, transformando o cotidiano em poesia com humor e ternura.',
                'cidade': 'Porto Alegre',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'adelia_prado',
                'email': 'adelia@livredia.com',
                'first_name': 'Adélia',
                'last_name': 'Prado',
                'bio': 'Poetisa do sagrado e do profano, celebra a vida cotidiana com olhar místico e sensível.',
                'cidade': 'Divinópolis',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'rubem_alves',
                'email': 'rubem@livredia.com',
                'first_name': 'Rubem',
                'last_name': 'Alves',
                'bio': 'Educador e ensaísta, suas crônicas são convites à reflexão sobre a vida e a felicidade.',
                'cidade': 'Campinas',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'martha_medeiros',
                'email': 'martha@livredia.com',
                'first_name': 'Martha',
                'last_name': 'Medeiros',
                'bio': 'Cronista do amor e das relações humanas, escreve com sinceridade sobre a vida moderna.',
                'cidade': 'Porto Alegre',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'affonso_solano',
                'email': 'affonso@livredia.com',
                'first_name': 'Affonso',
                'last_name': 'Romano de Sant\'Anna',
                'bio': 'Poeta e ensaísta, observador crítico da cultura brasileira contemporânea.',
                'cidade': 'Belo Horizonte',
                'pais': 'Brasil',
                'pseudonimo': 'A. Romano',
            },
            {
                'username': 'eliane_brum',
                'email': 'eliane@livredia.com',
                'first_name': 'Eliane',
                'last_name': 'Brum',
                'bio': 'Jornalista e escritora, suas crônicas dão voz aos invisíveis e questionam o status quo.',
                'cidade': 'Porto Alegre',
                'pais': 'Brasil',
                'pseudonimo': None,
            },
            {
                'username': 'joao_cabral',
                'email': 'cabral@livredia.com',
                'first_name': 'João',
                'last_name': 'Cabral de Melo Neto',
                'bio': 'Poeta da precisão e da geometria, seus versos são construções arquitetônicas de palavras.',
                'cidade': 'Recife',
                'pais': 'Brasil',
                'pseudonimo': 'J.C. Melo',
            },
        ]

        autores = []
        for data in autores_data:
            autor, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': User.Role.AUTOR,
                    'is_active': True,
                    'bio': data['bio'],
                    'cidade': data['cidade'],
                    'pais': data['pais'],
                    'pseudonimo': data['pseudonimo'],
                }
            )
            if created:
                autor.set_password('livredia2025')  # Senha padrão
                autor.save()
                autores.append(autor)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {autor.get_full_name()}'))
            else:
                autores.append(autor)
                self.stdout.write(self.style.WARNING(f'  ⚠ {autor.get_full_name()} já existia'))

        return autores

    def criar_tags(self):
        """Cria tags para classificação dos textos"""
        self.stdout.write('\n🏷️  Criando tags...')

        tags_nomes = [
            'Crônica', 'Poesia', 'Ensaio', 'Cotidiano', 'Ficção',
            'Filosofia', 'Reflexão', 'Memória', 'Amor', 'Cidade',
            'Tempo', 'Natureza', 'Sociedade', 'Arte', 'Literatura'
        ]

        tags = []
        for nome in tags_nomes:
            tag, created = Tag.objects.get_or_create(nome=nome)
            tags.append(tag)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ {nome}'))
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ {nome} já existia'))

        return tags

    def criar_textos(self, autores, tags):
        """Cria textos publicados"""
        self.stdout.write('\n📝 Criando textos...')

        textos_data = [
            {
                'titulo': 'A Solidão das Palavras Não Ditas',
                'subtitulo': 'Uma crônica sobre o silêncio que ecoa em nós',
                'conteudo': '''<p>Havia um tempo em que as palavras eram pontes, construídas com a madeira rústica da sinceridade e a argamassa da intenção. Hoje, parecem ter se tornado muros. Muros altos, impenetráveis, erguidos com os tijolos do não-dito e o cimento do medo. Vivemos na era da comunicação instantânea, mas nunca estivemos tão silenciosos.</p>
<p>Caminho pelas ruas e vejo rostos iluminados por telas, mas obscurecidos pela ausência de diálogo real. Sorrisos são emojis, abraços são GIFs, e "eu te amo" virou uma sigla fria enviada por um aplicativo.</p>
<p>Quantas histórias de amor não começaram por uma palavra não dita? Quantas amizades se desfizeram pela falta de uma explicação? A solidão das palavras não ditas é uma companheira cruel.</p>
<p>Escrevo não como quem tem as respostas, mas como quem compartilha a mesma angústia. Talvez seja a hora de desarmar os espíritos, de demolir os muros e voltar a construir pontes. Uma palavra de cada vez.</p>''',
                'tags_nomes': ['Crônica', 'Reflexão', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Mar de Dentro',
                'subtitulo': 'Poema sobre as profundezas da alma',
                'conteudo': '''<p>Há um mar que habita em mim,<br>
profundo como o tempo,<br>
vasto como o silêncio<br>
que precede a tempestade.</p>
<p>Suas ondas quebram<br>
nas praias secretas da memória,<br>
trazendo conchas de momentos perdidos,<br>
algas de sonhos esquecidos.</p>
<p>Navego neste mar interior<br>
sem bússola, sem porto,<br>
apenas a certeza incerta<br>
de que sou feito de água e sal.</p>''',
                'tags_nomes': ['Poesia', 'Reflexão', 'Natureza'],
                'display_autoria': 'PSEUDONIMO',
            },
            {
                'titulo': 'O Peso do Cotidiano',
                'subtitulo': 'Reflexões sobre a rotina que nos define',
                'conteudo': '''<p>Acordamos, escovamos os dentes, tomamos café. Repetimos gestos milenares que nos conectam a todos os humanos que já viveram. Há algo de sagrado nessa repetição, nessa liturgia silenciosa do ordinário.</p>
<p>O filósofo francês Michel de Certeau dizia que o cotidiano é a arte de fazer. Cada gesto banal é uma escolha, uma criação microscópica de sentido em meio ao caos. Quando preparo um café, não estou apenas fazendo café – estou decidindo como começar o dia, que ritmo dar às próximas horas.</p>
<p>A modernidade nos vendeu a ideia de que a vida só vale a pena nos momentos extraordinários. Precisamos de viagens épicas, conquistas monumentais, paixões arrebatadoras. Mas e as terças-feiras cinzentas? E os jantares silenciosos? E as tardes sem nada especial acontecendo?</p>
<p>Talvez seja justamente ali, no peso do cotidiano, que encontramos quem realmente somos. Não na exceção, mas na regra. Não no ápice, mas no platô.</p>''',
                'tags_nomes': ['Ensaio', 'Filosofia', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Carta a Um Desconhecido',
                'subtitulo': 'Crônica sobre conexões improváveis',
                'conteudo': '''<p>Caro desconhecido que cruzou comigo na estação de metrô hoje às 18h32,</p>
<p>Você não me viu. Eu também não deveria ter te visto – afinal, éramos apenas dois corpos se movendo em direções opostas no formigueiro urbano. Mas te vi. Vi o livro debaixo do seu braço (Clarice Lispector, como não reparar?), vi o cadarço desatado do seu tênis esquerdo, vi o cansaço honesto no seu rosto.</p>
<p>Pensei em te avisar sobre o cadarço. Quase o fiz. Mas o metrô chegou, você entrou, eu fiquei. E agora carrego comigo essa pequena história que só eu conheço: a história de alguém que quase falou com você mas não falou.</p>
<p>Vivemos cercados de quases. Quase conexões, quase conversas, quase amizades. Somos especialistas em passar ao lado uns dos outros sem realmente nos encontrarmos.</p>
<p>Espero que tenha chegado bem em casa. Espero que o cadarço não tenha causado nenhum tropeço. Espero que Clarice tenha te oferecido as palavras que eu não soube dizer.</p>''',
                'tags_nomes': ['Crônica', 'Cidade', 'Reflexão'],
                'display_autoria': 'AMBOS',
            },
            {
                'titulo': 'Ode à Procrastinação',
                'subtitulo': 'Um elogio à arte de adiar',
                'conteudo': '''<p>Depois eu faço.<br>
Amanhã eu começo.<br>
Segunda-feira é o dia perfeito para mudar de vida.</p>
<p>Dizem que procrastinar é defeito,<br>
preguiça, falta de disciplina.<br>
Eu digo: é resistência poética<br>
contra a tirania do produtivo.</p>
<p>Procrastino, logo existo.<br>
No espaço entre o dever e o fazer<br>
habita toda a minha humanidade.</p>
<p>Farei este poema terminar<br>
algum dia, quem sabe,<br>
quando der vontade,<br>
se der vontade.</p>''',
                'tags_nomes': ['Poesia', 'Cotidiano', 'Reflexão'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'A Geometria dos Afetos',
                'subtitulo': 'Ensaio sobre as formas do amor',
                'conteudo': '''<p>O amor, nos ensinaram, é um círculo. Completo, perfeito, sem começo nem fim. Mas vivendo o amor, descobrimos que ele raramente é circular. É mais frequentemente angular, irregular, assimétrico.</p>
<p>Há amores triângulos, com suas tensões e seus vértices afiados. Amores espirais, que crescem sem nunca se fechar. Amores paralelos, que correm lado a lado sem nunca se tocarem completamente.</p>
<p>O amor que vivi no último verão era um polígono de muitos lados – às vezes hexágono nos dias bons, às vezes pentágono quando faltava algo. Tentamos forçá-lo a ser círculo, a se encaixar na forma que os poemas prescrevem.</p>
<p>Mas talvez a beleza do afeto esteja justamente em sua geometria variável, em sua recusa a se conformar. Talvez amar seja aceitar que alguns formatos são irregulares, incompletos, e ainda assim suficientes.</p>''',
                'tags_nomes': ['Ensaio', 'Amor', 'Filosofia'],
                'display_autoria': 'PSEUDONIMO',
            },
            {
                'titulo': 'Inventário de Uma Tarde',
                'subtitulo': 'Poema-lista das pequenas coisas',
                'conteudo': '''<p>Uma xícara de café esquecida na mesa,<br>
já fria, com círculos de espuma nas bordas.</p>
<p>O barulho distante de uma britadeira<br>
destruindo e construindo simultaneamente.</p>
<p>Três pássaros na fiação elétrica,<br>
decidindo qual direção seguir.</p>
<p>A luz de quatro e meia da tarde,<br>
aquela que deixa tudo dourado e melancólico.</p>
<p>O peso súbito da consciência<br>
de que esta tarde específica<br>
nunca mais voltará a acontecer.</p>
<p>Este inventário incompleto<br>
de um momento que já passou<br>
enquanto eu ainda o descrevia.</p>''',
                'tags_nomes': ['Poesia', 'Cotidiano', 'Tempo'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Elogio da Solidão',
                'subtitulo': 'Crônica sobre o prazer de estar só',
                'conteudo': '''<p>Descobri tarde demais que a solidão é um luxo, não uma maldição. Durante anos fugi dela como se fosse um abismo. Enchia meus dias de gente, de barulho, de compromissos, qualquer coisa para não ficar a sós comigo mesma.</p>
<p>Até que um dia, por acidente ou cansaço, me vi sozinha numa tarde de domingo. Sem planos, sem obrigações, sem ninguém para entreter ou impressionar. E descobri que o abismo era, na verdade, um jardim.</p>
<p>Na solidão aprendi a ouvir meus próprios pensamentos sem o ruído dos outros. Aprendi que estar só não é estar abandonada, é estar em boa companhia – a minha própria.</p>
<p>Claro que ainda gosto de gente. Mas agora escolho melhor de quem me cercar. Porque aprendi que nada que venha de fora deveria ser melhor do que a paz que encontro aqui dentro.</p>''',
                'tags_nomes': ['Crônica', 'Reflexão', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Haicais Urbanos',
                'subtitulo': 'Fragmentos poéticos da cidade',
                'conteudo': '''<p>Metrô lotado —<br>
tantos destinos juntos<br>
por alguns minutos</p>
<p>Vidraça suja<br>
reflete meu rosto turvo<br>
quem sou nesta pressa?</p>
<p>Sinal vermelho<br>
um vendedor de sonhos<br>
que ninguém compra</p>
<p>Noite na cidade —<br>
luzes acesas escondem<br>
estrelas distantes</p>
<p>Entre edifícios<br>
um cachorro late sozinho<br>
eco sem resposta</p>''',
                'tags_nomes': ['Poesia', 'Cidade', 'Reflexão'],
                'display_autoria': 'PSEUDONIMO',
            },
            {
                'titulo': 'A Memória do Cheiro de Café',
                'subtitulo': 'Ensaio sobre os gatilhos sensoriais da lembrança',
                'conteudo': '''<p>Proust tinha sua madeleine. Eu tenho o café. Não qualquer café – o café coado devagar, numa manhã de domingo, quando a casa ainda está silenciosa e o sol entra pela janela da cozinha num ângulo específico que só acontece naquele horário.</p>
<p>O filósofo Gaston Bachelard dizia que a casa é nosso canto do mundo, nosso primeiro universo. E o cheiro do café é, para mim, a assinatura olfativa desse universo. Cada vez que o sinto, não estou apenas no presente – estou simultaneamente em todas as manhãs de domingo da minha vida.</p>
<p>Estou na casa da minha avó, aos sete anos, vendo-a coar café enquanto conta histórias. Estou no meu primeiro apartamento sozinha, aos vinte, descobrindo que fazer café para si mesma é um ato de autocuidado. Estou aqui, agora, aos quarenta, entendendo que a memória não mora no passado – ela mora nos cheiros, nos sabores, nos rituais repetidos.</p>
<p>A neurociência explica que o olfato tem conexão direta com a amígdala, região do cérebro responsável pela emoção e pela memória. Mas a ciência não consegue capturar a magia de como um cheiro pode nos transportar completamente no tempo.</p>''',
                'tags_nomes': ['Ensaio', 'Memória', 'Filosofia'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Conversa com o Tempo',
                'subtitulo': 'Diálogo impossível sobre a passagem dos dias',
                'conteudo': '''<p>— Por que você corre tanto? — perguntei ao Tempo.<br>
— Não corro — ele respondeu. — Você é que está parado.</p>
<p>— Mas ontem foi outro dia, e amanhã será diferente.<br>
— Ontem e amanhã são ilusões que você inventou. Eu só conheço agora.</p>
<p>— Então por que as pessoas envelhecem?<br>
— Não envelhecem. Apenas mudam. Você é que insiste em contar.</p>
<p>— E os mortos? Para onde vão?<br>
— Permanecem. No agora de cada um que os lembra.</p>
<p>— Isso é bonito, mas não consola.<br>
— Consolo é coisa de quem teme. Eu não temo. Apenas sou.</p>
<p>E assim o Tempo seguiu sendo, enquanto eu continuava tentando entendê-lo.</p>''',
                'tags_nomes': ['Crônica', 'Filosofia', 'Tempo'],
                'display_autoria': 'AMBOS',
            },
            {
                'titulo': 'A Cor do Tédio',
                'subtitulo': 'Crônica sobre o vazio produtivo',
                'conteudo': '''<p>O tédio tem cor. É cinza, mas não o cinza dramático das tempestades ou o cinza elegante do concreto moderno. É o cinza da segunda-feira às três da tarde, quando o dia já perdeu a frescura da manhã mas ainda falta muito para acabar.</p>
<p>Nossa sociedade trata o tédio como inimigo. "Não fique parado", "seja produtivo", "aproveite cada minuto". Como se o vazio fosse um erro de programação que precisasse ser corrigido imediatamente.</p>
<p>Mas foi no tédio que escrevi meus melhores poemas. Foi no vazio de uma tarde cinzenta que tive a ideia que mudou meu trabalho. Foi na ausência absoluta de estímulos que encontrei, finalmente, meus próprios pensamentos.</p>
<p>O tédio é solo fértil. Dele nascem as ideias que realmente importam, as que não estão competindo por atenção com mil outros estímulos. Talvez precisemos de mais tardes cinzentas, mais momentos vazios, mais tédio produtivo.</p>''',
                'tags_nomes': ['Crônica', 'Reflexão', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Elegia para as Livrarias',
                'subtitulo': 'Poema sobre os templos da palavra',
                'conteudo': '''<p>Há templos que não precisam de sinos<br>
nem vitrais coloridos:<br>
basta o cheiro de papel e tinta,<br>
o silêncio entre as estantes.</p>
<p>Entro numa livraria como quem entra em casa<br>
após longa viagem —<br>
os livros me reconhecem,<br>
eu reconheço os livros.</p>
<p>Em cada prateleira, um universo paralelo<br>
esperando ser descoberto.<br>
Em cada capa, uma promessa<br>
de que existem vidas além da minha.</p>
<p>Dizem que as livrarias estão morrendo,<br>
que o digital as substituirá.<br>
Mas como substituir o ritual<br>
de folhear o desconhecido?</p>
<p>Enquanto houver quem busque<br>
o peso real das palavras nas mãos,<br>
haverá livrarias —<br>
faróis em tempos de telas.</p>''',
                'tags_nomes': ['Poesia', 'Literatura', 'Arte'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Manual de Instruções para Viver',
                'subtitulo': 'Ensaio irônico sobre a impossibilidade de guias',
                'conteudo': '''<p>1. Acorde todos os dias no mesmo horário. Ou não. A constância é superestimada.</p>
<p>2. Faça exercícios. Dizem que é bom para a saúde. Mas sua avó nunca pisou numa academia e viveu até os noventa.</p>
<p>3. Persiga seus sonhos. A menos que seus sonhos sejam impraticáveis, então seja realista. Mas não seja realista demais, senão você desiste de tudo.</p>
<p>4. Seja você mesmo. Exceto se você for chato, aí melhore um pouco.</p>
<p>5. O sucesso vem para quem trabalha duro. Exceto quando não vem. Nesse caso, a culpa é do sistema, do mercado, da sorte ou de Mercúrio retrógrado.</p>
<p>Como podem ver, todos os manuais de vida se contradizem porque não existe manual. Existe apenas o improviso honesto de quem acorda todo dia sem saber exatamente o que está fazendo, mas faz mesmo assim.</p>
<p>Talvez esse seja o único conselho válido: faça mesmo sem saber. Porque ninguém sabe, e está tudo bem.</p>''',
                'tags_nomes': ['Ensaio', 'Cotidiano', 'Reflexão'],
                'display_autoria': 'PSEUDONIMO',
            },
            {
                'titulo': 'O Silêncio Entre Notas',
                'subtitulo': 'Crônica sobre música e vazios',
                'conteudo': '''<p>Um professor de música me disse uma vez que o silêncio é tão importante quanto o som. Na partitura, há símbolos para as pausas – momentos em que nada deve ser tocado. Sem essas pausas, a música seria apenas barulho.</p>
<p>Penso nisso quando olho para a minha vida. Vivemos numa cultura que valoriza apenas as notas, nunca os silêncios. Precisamos estar sempre fazendo, produzindo, acontecendo. O vazio nos apavora.</p>
<p>Mas e se o vazio for essencial? E se, assim como na música, nossas vidas precisarem de pausas para fazer sentido?</p>
<p>Tentei isso uma vez: uma semana sem compromissos. Sem encontros marcados, sem projetos, sem metas. Apenas pausas. Os primeiros dias foram agonia. Não sabia o que fazer com tanto silêncio. Mas no quarto dia, algo mudou. Comecei a ouvir a melodia da minha própria vida.</p>
<p>Descobri que não sou apenas as notas que toco, mas também os silêncios que permito. E que ambos, juntos, compõem a música que escolho viver.</p>''',
                'tags_nomes': ['Crônica', 'Arte', 'Reflexão'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Arqueologia Doméstica',
                'subtitulo': 'Poema sobre os vestígios do cotidiano',
                'conteudo': '''<p>No fundo da gaveta encontrei:<br>
três canetas sem tinta,<br>
um chaveiro de lugar que não lembro,<br>
bilhetes escritos em letra que já não é minha.</p>
<p>Cada objeto uma camada geológica<br>
da pessoa que fui.<br>
Escavo minha própria casa<br>
como quem busca civilizações perdidas.</p>
<p>Este recibo amarelado de 2015,<br>
esta foto desbotada,<br>
este botão sem camisa —<br>
fósseis de versões antigas de mim.</p>
<p>Guardo tudo de novo.<br>
Fecho a gaveta.<br>
Um dia alguém vai encontrar<br>
e tentar decifrar quem fui.</p>
<p>Boa sorte.<br>
Nem eu mesma sei mais.</p>''',
                'tags_nomes': ['Poesia', 'Memória', 'Cotidiano'],
                'display_autoria': 'AMBOS',
            },
            {
                'titulo': 'A Filosofia da Fila de Supermercado',
                'subtitulo': 'Ensaio sobre microcosmos sociais',
                'conteudo': '''<p>A fila do supermercado é um laboratório social perfeito. Ali, em miniatura, vemos todas as dinâmicas humanas: a disputa por poder (qual fila anda mais rápido?), a solidariedade (deixar passar quem tem poucos itens), a injustiça (os furadores de fila), a paciência ou a falta dela.</p>
<p>O sociólogo Erving Goffman diria que estamos todos "representando" nossos papéis sociais. A mulher que reclama alto está performando indignação. O senhor que espera calado está performando estoicismo. Eu, fingindo ler os tabloides, estou performando desinteresse enquanto absorvo cada fofoca.</p>
<p>Há uma democracia estranha na fila. Não importa se você é CEO ou desempregado – todos esperamos igualmente. Claro que essa democracia é ilusória (o rico pode pedir delivery), mas por alguns minutos, compartilhamos a mesma condição: a espera.</p>
<p>E esperar é, talvez, a mais humana das atividades. Esperamos na fila, esperamos pelo amor, esperamos por mudanças. Toda a vida é uma grande fila para algo que pode ou não valer a pena quando finalmente chegarmos lá.</p>''',
                'tags_nomes': ['Ensaio', 'Sociedade', 'Filosofia'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Receita de Felicidade',
                'subtitulo': 'Crônica culinária existencial',
                'conteudo': '''<p>Ingredientes:<br>
- 1 xícara de expectativas reduzidas<br>
- 200g de presentes genuínos<br>
- 3 colheres de sopa de bom humor<br>
- Um punhado de amigos verdadeiros<br>
- Gratidão a gosto</p>
<p>Modo de preparo:<br>
Misture as expectativas reduzidas com os presentes genuínos até formar uma massa homogênea de aceitação. Adicione o bom humor aos poucos, mexendo sempre para não empelotar.</p>
<p>Numa forma untada com compaixão, disponha os amigos verdadeiros em camadas. Leve ao forno da experiência por tempo indeterminado – cada pessoa tem seu próprio tempo de cozimento.</p>
<p>Finalize com gratidão espalhada generosamente por cima. Sirva quente, de preferência compartilhado.</p>
<p>Observações:<br>
Esta receita nunca sai igual duas vezes. O segredo não está em seguir as instruções perfeitamente, mas em improvisar com o que você tem à mão. E lembrar: felicidade caseira sempre tem gosto melhor que a industrializada.</p>''',
                'tags_nomes': ['Crônica', 'Cotidiano', 'Reflexão'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Paisagem com Melancolia',
                'subtitulo': 'Poema contemplativo sobre tardes que passam',
                'conteudo': '''<p>A tarde se arrasta<br>
como gato preguiçoso<br>
pelo telhado das horas.</p>
<p>Há uma melancolia bonita<br>
no jeito que a luz morre devagar,<br>
sem pressa, sem drama.</p>
<p>Sento na varanda<br>
com uma xícara de chá esfriando<br>
e nenhuma urgência.</p>
<p>No horizonte, o dia se despede<br>
com sua paleta de laranjas e roxos —<br>
pintor impressionista que não assina suas obras.</p>
<p>Alguém passa na rua.<br>
Um cachorro late longe.<br>
A vida acontecendo em seu ritmo próprio.</p>
<p>E eu aqui,<br>
testemunha silenciosa<br>
desta pequena, perfeita e melancólica tarde.</p>''',
                'tags_nomes': ['Poesia', 'Natureza', 'Tempo'],
                'display_autoria': 'PSEUDONIMO',
            },
            {
                'titulo': 'A Arte da Conversa Fiada',
                'subtitulo': 'Ensaio sobre a importância do banal',
                'conteudo': '''<p>"Como vai?" "Bem, e você?" "Tudo certo." Esta é, provavelmente, a conversa mais repetida no mundo. Banal, vazia, sem conteúdo real. E, no entanto, absolutamente essencial.</p>
<p>A conversa fiada é o óleo que lubrifica as engrenagens sociais. Sem ela, toda interação seria densa, profunda, exaustiva. Imagine se cada "oi" no corredor fosse uma oportunidade para discussões existenciais.</p>
<p>O antropólogo Bronisław Malinowski chamava isso de "comunhão fática" – linguagem cuja função não é transmitir informação, mas estabelecer e manter conexão social. Quando comento sobre o tempo com o porteiro, não estou realmente interessada em meteorologia. Estou dizendo: "Vejo você. Reconheço sua existência. Fazemos parte do mesmo mundo."</p>
<p>Em tempos de hiperconectividade digital, perdemos a arte da conversa fiada. Queremos que cada interação seja significativa, profunda, digna de ser postada. Mas às vezes o significado está justamente na falta de profundidade.</p>
<p>Às vezes, falar sobre o tempo é simplesmente falar sobre o tempo. E isso também é bonito.</p>''',
                'tags_nomes': ['Ensaio', 'Sociedade', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Canção do Desapego',
                'subtitulo': 'Poema sobre deixar ir',
                'conteudo': '''<p>Aprendi tarde demais<br>
que agarrar é ferir —<br>
as mãos machucam de tanto segurar<br>
o que já decidiu partir.</p>
<p>Deixo ir:<br>
o amor que não ficou,<br>
os sonhos que murcharam,<br>
as versões de mim que foram<br>
mas não são mais.</p>
<p>Há uma liberdade amarga<br>
em abrir as mãos,<br>
em ver voar para longe<br>
aquilo que pensei ser meu.</p>
<p>Nada é meu.<br>
Nem sequer eu mesma<br>
pertenço a esta versão de mim<br>
que em breve também deixarei ir.</p>
<p>Sou todas as perdas,<br>
todos os desapegos,<br>
todos os "adeus" que aprendi a dizer<br>
sem morrer um pouco.</p>''',
                'tags_nomes': ['Poesia', 'Reflexão', 'Amor'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'A Biblioteca dos Livros Não Lidos',
                'subtitulo': 'Crônica sobre a pilha que nos persegue',
                'conteudo': '''<p>Ao lado da minha cama, uma pilha acusa: dezessete livros comprados com as melhores intenções, não lidos. Alguns ali há anos. Todos olhando para mim com reprovação silenciosa.</p>
<p>O escritor Umberto Eco dizia que uma biblioteca particular não deve conter apenas livros lidos, mas especialmente os não lidos – eles representam nossa infinita capacidade de aprender. Minha pilha, então, não é vergonha, mas ambição.</p>
<p>Compro livros não para a pessoa que sou, mas para a pessoa que pretendo ser. Aquela que lê sobre astrofísica (spoiler: não leio), que finalmente entende economia (ainda não), que tem tempo para poesia de 500 páginas (quando?).</p>
<p>Cada livro não lido é uma promessa adiada. Uma conversa que ainda teremos, eu e aquele autor, num futuro sempre recuado. "Amanhã começo", digo há três anos sobre o mesmo romance russo.</p>
<p>Mas sabe? Acho que está tudo bem. A pilha me lembra que ainda há mundos a descobrir, ideias a explorar, versões minhas que ainda não conheço. Mesmo que nunca leia todos, é reconfortante saber que eles estão ali, esperando.</p>''',
                'tags_nomes': ['Crônica', 'Literatura', 'Cotidiano'],
                'display_autoria': 'AMBOS',
            },
            {
                'titulo': 'Pastoral Urbana',
                'subtitulo': 'Poema sobre natureza entre concreto',
                'conteudo': '''<p>No canteiro esquecido da avenida<br>
nasce um girassol improvável —<br>
dourado desafio ao cinza,<br>
teimosia amarela entre pneus.</p>
<p>Ninguém plantou.<br>
Ninguém rega.<br>
E no entanto ele insiste<br>
em buscar o sol acima do asfalto.</p>
<p>Há passarinho cantando<br>
na antena do prédio,<br>
formiga carregando folha<br>
pelo meio-fio.</p>
<p>A natureza não desistiu das cidades —<br>
apenas aprendeu a viver nos espaços<br>
que deixamos entre nossa pressa.</p>
<p>E às vezes, no engarrafamento,<br>
vejo o girassol teimoso<br>
e lembro: também sou natureza<br>
insistindo em florescer onde me plantaram.</p>''',
                'tags_nomes': ['Poesia', 'Natureza', 'Cidade'],
                'display_autoria': 'REAL',
            },
            {
                'titulo': 'Tratado sobre o Erro',
                'subtitulo': 'Ensaio sobre a beleza do imperfeito',
                'conteudo': '''<p>Minha filha chegou da escola chorando. Tinha tirado 7 numa prova. "Errei três questões", soluçava, como se o mundo tivesse acabado. Tentei consolá-la, mas percebi: eu mesma lhe ensinei que errar é fracasso.</p>
<p>Vivemos numa cultura da perfeição. Instagram mostra apenas acertos. Currículos listam sucessos. Ninguém posta foto do bolo que desandou, da apresentação que travou, do projeto que falhou. E assim aprendemos a ter vergonha dos erros, a escondê-los como se fossem defeitos de caráter.</p>
<p>Mas a verdade é: erramos mais do que acertamos. E é assim que aprendemos. Thomas Edison errou mil vezes antes de acertar a lâmpada. Cada erro era informação, não fracasso. "Não falhei", dizia ele, "apenas descobri mil formas que não funcionam."</p>
<p>Estou tentando reaprender isso: o erro não é o oposto do sucesso, é parte do processo. Cada vez que erro, estou um passo mais perto de acertar. Cada tropeço me ensina onde pisar melhor na próxima.</p>
<p>Olhei para minha filha e disse: "Sabe o que é incrível? Você descobriu três coisas que ainda precisa aprender. Isso não é fracasso, é mapa."</p>''',
                'tags_nomes': ['Ensaio', 'Reflexão', 'Cotidiano'],
                'display_autoria': 'REAL',
            },
        ]

        textos = []
        for i, data in enumerate(textos_data):
            # Calcular data de publicação (últimos 6 meses, distribuído)
            dias_atras = random.randint(1, 180)
            data_pub = timezone.now() - timedelta(days=dias_atras)

            # Escolher autor aleatório
            autor = random.choice(autores)

            # Criar slug único
            base_slug = data['titulo'].lower()
            base_slug = base_slug.replace(' ', '-').replace(',', '').replace(':', '')
            slug = f"{base_slug}-{data_pub.strftime('%Y%m')}"

            texto, created = Texto.objects.get_or_create(
                slug=slug,
                defaults={
                    'autor': autor,
                    'titulo': data['titulo'],
                    'subtitulo': data['subtitulo'],
                    'conteudo': data['conteudo'],
                    'status': Texto.Status.PUBLICADO,
                    'data_publicacao': data_pub,
                    'selo_livre_ia': True,
                    'permite_comentarios': True,
                    'moderacao_automatica': True,
                    'display_autoria': data.get('display_autoria', 'REAL'),
                }
            )

            if created:
                # Adicionar tags
                for tag_nome in data['tags_nomes']:
                    tag = Tag.objects.get(nome=tag_nome)
                    texto.tags.add(tag)

                textos.append(texto)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {texto.titulo[:50]}...'))
            else:
                textos.append(texto)
                self.stdout.write(self.style.WARNING(f'  ⚠ {texto.titulo[:50]}... já existia'))

        return textos

    def criar_visualizacoes(self, textos):
        """Cria visualizações para os textos"""
        self.stdout.write('\n👁️  Criando visualizações...')

        total = 0
        for texto in textos:
            # Número aleatório de visualizações (alguns textos mais populares)
            num_views = random.randint(5, 50)

            for _ in range(num_views):
                dias_atras = random.randint(0, 90)
                data_view = timezone.now() - timedelta(days=dias_atras)

                # 70% anônimas, 30% de usuários
                usuario = None
                if random.random() > 0.7:
                    # Pegar um usuário leitor (vamos criar depois)
                    pass

                Visualizacao.objects.create(
                    texto=texto,
                    usuario=usuario,
                    data_visualizacao=data_view,
                    tempo_permanencia=random.randint(30, 600),  # 30s a 10min
                    ip_address=f"192.168.1.{random.randint(1, 255)}",
                    sessao_id=f"sess_{random.randint(10000, 99999)}"
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {total} visualizações criadas'))

    def criar_leitores(self):
        """Cria alguns usuários leitores"""
        self.stdout.write('\n👥 Criando leitores...')

        leitores_data = [
            {'username': 'maria_silva', 'email': 'maria@email.com', 'first_name': 'Maria', 'last_name': 'Silva'},
            {'username': 'joao_santos', 'email': 'joao@email.com', 'first_name': 'João', 'last_name': 'Santos'},
            {'username': 'ana_costa', 'email': 'ana@email.com', 'first_name': 'Ana', 'last_name': 'Costa'},
            {'username': 'pedro_oliveira', 'email': 'pedro@email.com', 'first_name': 'Pedro', 'last_name': 'Oliveira'},
        ]

        leitores = []
        for data in leitores_data:
            leitor, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': User.Role.LEITOR,
                    'is_active': True,
                }
            )
            if created:
                leitor.set_password('livredia2025')
                leitor.save()
                leitores.append(leitor)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {leitor.get_full_name()}'))
            else:
                leitores.append(leitor)
                self.stdout.write(self.style.WARNING(f'  ⚠ {leitor.get_full_name()} já existia'))

        return leitores

    def criar_comentarios(self, textos, autores, leitores):
        """Cria comentários aprovados nos textos"""
        self.stdout.write('\n💬 Criando comentários...')

        comentarios_exemplos = [
            "Texto maravilhoso! Me identifiquei muito.",
            "Que reflexão profunda. Obrigado por compartilhar.",
            "Suas palavras sempre tocam no ponto certo.",
            "Lindo! Vou reler várias vezes.",
            "Exatamente o que eu precisava ler hoje.",
            "Que escrita sensível e honesta.",
            "Me emocionei com este texto.",
            "Perfeita análise da questão.",
            "Texto necessário nestes tempos.",
            "Suas crônicas são sempre um presente.",
            "Poesia pura! Parabéns.",
            "Concordo totalmente. Muito bem colocado.",
            "Que beleza de texto!",
            "Suas palavras ecoam em mim.",
            "Gratidão por este momento de leitura.",
        ]

        total = 0
        # Adicionar comentários a alguns textos aleatórios
        textos_com_comentarios = random.sample(list(textos), min(15, len(textos)))

        for texto in textos_com_comentarios:
            num_comentarios = random.randint(1, 3)

            for _ in range(num_comentarios):
                # Escolher se é de leitor ou anônimo
                if random.random() > 0.3 and leitores:
                    autor_comentario = random.choice(leitores)
                    anonimo = False
                else:
                    # Comentário de um autor sobre texto de outro
                    outros_autores = [a for a in autores if a != texto.autor]
                    if outros_autores:
                        autor_comentario = random.choice(outros_autores)
                        anonimo = random.choice([True, False])
                    else:
                        continue

                dias_atras = random.randint(0, 60)
                data_comentario = timezone.now() - timedelta(days=dias_atras)

                Comentario.objects.create(
                    texto=texto,
                    autor=autor_comentario,
                    conteudo=random.choice(comentarios_exemplos),
                    status=Comentario.Status.APROVADO,
                    publicado_anonimamente=anonimo,
                    data_publicacao=data_comentario
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {total} comentários criados'))

    def exibir_resumo(self):
        """Exibe resumo da população"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 RESUMO DA POPULAÇÃO'))
        self.stdout.write('='*60)

        self.stdout.write(f'\n👤 Autores: {User.objects.filter(role=User.Role.AUTOR).count()}')
        self.stdout.write(f'👥 Leitores: {User.objects.filter(role=User.Role.LEITOR).count()}')
        self.stdout.write(f'🏷️  Tags: {Tag.objects.count()}')
        self.stdout.write(f'📝 Textos publicados: {Texto.objects.filter(status=Texto.Status.PUBLICADO).count()}')
        self.stdout.write(f'👁️  Visualizações: {Visualizacao.objects.count()}')
        self.stdout.write(f'💬 Comentários: {Comentario.objects.count()}')
        self.stdout.write(f'📄 Páginas estáticas: {PaginaEstatica.objects.count()}')

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✨ Dados prontos para testar as telas da FASE 2!'))
        self.stdout.write('='*60 + '\n')
