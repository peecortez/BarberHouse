# BarberHouse

Sistema web para gerenciamento de uma barbearia, desenvolvido com Django. Clientes podem consultar serviços e profissionais com agenda aberta, verificar horários disponíveis e acompanhar seus agendamentos. Profissionais podem gerenciar a própria agenda e atualizar o status dos atendimentos.

## Funcionalidades

- Cadastro e login de clientes e profissionais, com CPF validado (dígitos verificadores e unicidade), previsto para validação de cupons e promoções.
- Confirmação de e-mail no cadastro: a conta só é ativada pelo link enviado ao e-mail cadastrado (vale 24h). Quem tenta entrar antes de confirmar vê um botão para reenviar o link.
- Recuperação de senha: "Esqueceu a senha?" no login envia um link para criar uma nova senha (vale 2h e só pode ser usado uma vez).
- E-mails de agendamento para o cliente: horário reservado, confirmado pelo profissional, cancelado (com texto diferente se quem cancelou foi o profissional) e concluído (com o convite para avaliar).
- Lembrete por e-mail 24h antes do horário, para quem marcou com mais de um dia de antecedência. Cada agendamento recebe no máximo um.
- Avaliação do atendimento: depois de concluído, o cliente dá de 1 a 5 estrelas e um comentário opcional (uma vez por atendimento). O profissional vê a média e os comentários em "Minha agenda", e o cliente vê a média de cada profissional na hora de agendar.
- Avaliações na Home do cliente: abaixo do menu, a seção "O que dizem nossos clientes" mostra as 8 avaliações mais recentes que têm comentário, numa pilha de cards de vidro com a inicial do cliente (o ativo fica na frente e os outros atrás, girados). O comentário aparece palavra por palavra, e as setas ← → trocam a avaliação. Só aparece o primeiro nome de quem avaliou, e a tela de avaliar avisa que o comentário pode aparecer ali. Sem avaliações com comentário, a seção não aparece.
- Cadastro de serviços pelo painel administrativo do Django.
- Consulta de horários disponíveis por serviço, profissional e data.
- Criação e acompanhamento de agendamentos.
- Notificações (login, agendamento) no canto superior direito, alinhadas à barra de navegação. Ficam 6 segundos na tela, com uma barra de progresso que pausa enquanto o mouse está em cima, e podem ser fechadas no "x".
- Visualização separada de agendamentos ativos, concluídos e cancelados.
- Identificação de quem cancelou cada agendamento.
- Confirmação, conclusão e cancelamento de atendimentos, conforme o perfil do usuário.
- Abertura e fechamento da agenda do profissional.
- Notícia de promoção com código de 15% de desconto (`BARBER15OFF` + 3 últimos dígitos do CPF), um por CPF, exibido ao cliente logado. O cliente resgata o cupom em Notícias ("Pegue seu cupom aqui"), e o resgate fica gravado. Só então o profissional pode aplicá-lo ao concluir o atendimento: sem resgate, a opção nem aparece e o servidor recusa. Depois de usado, o cliente vê "Cupom já usado".
- Página Sobre (`/sobre/`, aberta a todos): a história (fictícia) da barbearia desde 2015 ao lado da foto da fachada, a galeria "Nosso espaço" com 3 fotos do salão e os contatos (WhatsApp, Instagram, TikTok, endereço e horário). Os contatos são fictícios e aparecem só como texto, sem link.
- Barra de navegação fixa em todas as telas internas, adaptada para celular. Ela fica transparente no topo e ganha fundo com desfoque ao rolar a página.
- Menu inicial com saudação pelo primeiro nome do usuário.
- Abertura da marca logo após o login: o logo aparece sobre fundo preto (o bigode se abre do centro para os lados) e a foto se abre do centro para as bordas.
- Transição animada entre páginas: na home, o card clicado vira o cabeçalho da página seguinte. Funciona no Chrome, Edge e Safari; no Firefox a página troca sem animação.
- Etiquetas coloridas de status nos agendamentos (agendado, confirmado, concluído e cancelado).
- Painel administrativo para gerenciar os dados do sistema.

## Tecnologias

- Python
- Django
- SQLite
- HTML, CSS e JavaScript

## Requisitos

- Python instalado.
- `pip` disponível no ambiente.

> As dependencias estao listadas em requirements.txt.

## Como executar localmente

No terminal, entre na pasta do projeto:

```bash
cd BarberHouse
```

Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
```

No Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

No macOS ou Linux:

```bash
source venv/bin/activate
```

Instale o Django:

```bash
python -m pip install -r requirements.txt
```

Aplique as migrações e inicie o servidor:

```bash
python manage.py migrate
python manage.py runserver
```

Abra <http://127.0.0.1:8000/> no navegador. O painel administrativo fica em <http://127.0.0.1:8000/admin/>.

Para criar um usuário administrador:

```bash
python manage.py createsuperuser
```

Cadastre serviços pelo painel administrativo antes de realizar agendamentos.

### E-mails (Gmail, sem custo)

Sem configuração nenhuma, os e-mails aparecem **no terminal** do `runserver`, inclusive os links de confirmação e de redefinir senha. Para enviar de verdade:

1. Use uma conta Gmail (de preferência uma só do projeto) com a **verificação em duas etapas** ativada.
2. Gere uma **senha de app** em <https://myaccount.google.com/apppasswords>. É uma senha de 16 letras, diferente da senha da conta.
3. Crie um arquivo `.env` na mesma pasta do `manage.py` com:

   ```text
   EMAIL_HOST_USER=sua.conta@gmail.com
   EMAIL_HOST_PASSWORD=abcdabcdabcdabcd
   ```

4. Reinicie o `runserver`.

Para quem acessa pelo túnel do `cloudflared`, coloque também `SITE_URL=https://xxxx.trycloudflare.com` no `.env`, para os links dos lembretes apontarem para o túnel. Os outros e-mails já usam o endereço por onde a pessoa acessou.

**Custos e segurança:**

- O Gmail por SMTP é gratuito (cerca de 500 e-mails por dia). Não existe cobrança: o pior caso é o Google pausar o envio por algumas horas.
- O `.env` está no `.gitignore`, então a senha de app nunca vai para o GitHub. Se a senha vazar, revogue em <https://myaccount.google.com/apppasswords> e gere outra.
- Teto diário de envios (`EMAIL_LIMITE_DIARIO`, padrão 100). Passou disso, o sistema para de enviar e registra no log.
- E-mails que qualquer pessoa pode pedir (reenviar confirmação, redefinir senha) têm limite de 1 por minuto e 5 por dia para cada endereço. Essas telas dão a mesma resposta exista ou não a conta.
- Os e-mails só vão para o endereço do próprio usuário cadastrado. Não existe tela onde se digite um destinatário.
- Todo envio fica registrado em **E-mails enviados**, no painel administrativo.
- Se o envio falhar (sem internet, senha errada), a ação no site continua normalmente e o erro vai para o log.

**Lembretes:** com o `runserver` ligado, uma tarefa em segundo plano verifica a cada 10 minutos (`LEMBRETES_INTERVALO_MIN`) os horários das próximas 24h. Para rodar na mão, ou pelo Agendador de Tarefas do Windows:

```bash
python manage.py enviar_lembretes
```

### Resetar o banco para uma apresentação

```bash
python manage.py resetar_demo
```

O comando apaga clientes, profissionais, agendamentos, avaliações, sessões e o registro de e-mails enviados (sem backup: os dados apagados não voltam) e cria 4 profissionais de demonstração com a senha `barber123`:

| Profissional  | E-mail                   |
|---------------|--------------------------|
| Rafael Souza  | rafael@barberhouse.com   |
| Bruno Lima    | bruno@barberhouse.com    |
| Diego Martins | diego@barberhouse.com    |
| Thiago Alves  | thiago@barberhouse.com   |

Se houver pelo menos um serviço cadastrado, o comando também cria 5 clientes de demonstração (Lucas, Gabriel, Matheus, Pedro e João, com e-mails `@cliente.demo`, por exemplo `lucas@cliente.demo`, e a mesma senha `barber123`), cada um com um atendimento concluído e uma avaliação. É isso que preenche a seção de avaliações da Home. Nenhum e-mail é enviado.

Os superusuários (admin) e os serviços continuam.

## Fluxo de uso

1. Crie uma conta como cliente ou profissional pela página de cadastro.
2. Confirme o e-mail pelo link recebido e entre com o e-mail e a senha cadastrados.
3. Como profissional, cadastre ou solicite que um administrador cadastre serviços e gerencie os agendamentos recebidos. A agenda começa aberta e pode ser fechada na interface.
4. Como cliente, escolha um serviço, um profissional disponível, uma data e um horário para agendar.
5. Acompanhe ou cancele seus agendamentos na área correspondente. Depois de concluído, avalie o atendimento.

Os horários são oferecidos em intervalos de 30 minutos entre 8h e 18h, considerando a duração do serviço e os agendamentos existentes.

## Estrutura do projeto

```text
BarberHouse/
├── agendamentos/       # Modelos, telas, formulários, rotas e arquivos estáticos
│   ├── emails.py       # Envio de e-mails (teto diário, limite por endereço, registro)
│   ├── lembretes.py    # Lembretes de 24h e a verificação em segundo plano
│   ├── templates/emails/  # Modelos dos e-mails (HTML + texto)
│   └── management/commands/
│       ├── resetar_demo.py      # Limpa o banco para apresentação
│       └── enviar_lembretes.py  # Envia os lembretes pendentes na mão
├── barbearia/          # Configurações e rotas principais do Django
├── manage.py           # Utilitário de administração do Django
└── db.sqlite3          # Banco SQLite local (criado/atualizado pelas migrações)
```

### Templates

As telas herdam de um layout comum em `agendamentos/templates/`:

- `base.html`: esqueleto de todas as páginas (viewport, fontes Geist e DM Sans, CSS, ícones e notificações).
- `base_auth.html`: login e cadastro, com o card centralizado.
- `base_app.html`: telas internas, com a barra de navegação fixa (links conforme o perfil, link ativo destacado e botão Sair).
- `recuperar_senha.html`, `recuperar_senha_enviado.html`, `redefinir_senha.html` e `redefinir_senha_concluido.html`: o fluxo de "Esqueceu a senha?", sobre `base_auth.html`.
- `avaliar.html`: a nota em estrelas e o comentário do atendimento. `_estrelas.html` mostra uma nota já dada.
- `_avaliacoes_destaque.html`: a seção de avaliações da Home do cliente. Todos os cards vêm prontos no HTML, e o `menu.js` (`ligarAvaliacoesDestaque`) só troca o ativo e anima.
- `sobre.html`: a página Sobre (história, "Nosso espaço" e contatos), com conteúdo fixo. As fotos ficam em `agendamentos/static/agendamentos/sobre/`, recortadas e comprimidas (até ~200 KB cada); os originais ficam em `referencias/sobre/`, fora do Git.
- `_logo.html`: o logo do login, do cadastro e da abertura, incluído com `{% include '_logo.html' with tamanho='auth' %}`. Os tamanhos são `auth` e `abertura`. Com `slogan=True`, mostra também "barbearia & estilo".

O tipo do usuário logado (`cliente` ou `profissional`) e o primeiro nome dele chegam a todos os templates como `tipo_usuario` e `primeiro_nome`, pelo context processor `agendamentos/context_processors.py`. O JavaScript das telas fica em `agendamentos/static/agendamentos/menu.js`, e os estilos em `barbearia.css`.

### Identidade visual

O logo oficial (bigode, "barberhouse" e o slogan "barbearia & estilo") foi adaptado para o tema escuro:

- **Home:** o logo completo animado (`referencias/logo-barberhouse-animada.svg`) fica colado direto no `home.html`, acima da saudação.
- **Barra de navegação:** só o bigode animado (`referencias/bigode-animado.svg`), colado direto no `base_app.html`. Ele leva para o Início e fica âmbar no hover.
- **Animação dos SVGs:** a metade esquerda do bigode gira de leve a cada 2,6s, com animação SMIL nativa do SVG. No logo da Home o giro é contínuo; na barra, só acontece com o mouse (ou o foco do teclado) em cima. Para quem ativa "reduzir movimento", o `menu.js` congela o bigode parado.
- **Cores:** os SVGs originais são escuros sobre creme. Aqui as cores vêm do CSS (`.svg-tinta`, `.svg-destaque` e `.svg-slogan`): o bigode e "barber" ficam claros, e "house" usa o âmbar da interface no lugar do ferrugem original (`#b9512a`).
- **Fonte:** o nome usa Inter 800 e o slogan Inter 400, carregadas pelo Google Fonts, como no design oficial.
- **Login, cadastro e abertura:** usam `_logo.html`. O bigode é uma máscara (`logo-bigode.png`) e o nome é texto em Inter.
- **Favicon:** `favicon.png` e `apple-touch-icon.png` mantêm as cores originais, com o bigode escuro sobre creme.

Tema escuro com um único acento âmbar (`#e2a053`), usado apenas no botão principal, no link ativo e no foco. Títulos em DM Sans peso 500, títulos de seção em Geist e botões e campos em formato de pílula. Na home, o título tem dois tons: a saudação em branco e a pergunta em cinza.

Todas as telas usam glassmorphism: uma foto em preto e branco fica ao fundo com um véu escuro, e os cards, a barra de navegação, os diálogos e as notificações são painéis de vidro translúcido com desfoque leve, borda clara, reflexo na borda superior e sombra suave. Cada tela pode ter a própria foto pelo bloco `classe_fundo` de `base_app.html`:

- `fundo-home` (poste de barbeiro, `fundo-home.jpg`): menu inicial.
- `fundo-agendamentos` (cadeira, `fundo-agendamentos.jpg`): Agendar e Meus agendamentos.
- Sem classe: a foto padrão (`fundo-barbearia.jpg`), usada também no login e no cadastro.

As fotos da página Sobre são a exceção ao preto e branco: ficam coloridas (o tom quente combina com o âmbar), com as bordas escurecidas e o corte preservando o alto da foto, onde estão os letreiros.

As cores, os raios, as fontes e a intensidade do vidro ficam em variáveis no topo de `barbearia.css` (`--cor-*`, `--raio-*`, `--fonte-*` e `--vidro-*`). Quem ativa "reduzir movimento" no sistema vê as telas sem animação e sem transição entre páginas.

## Observações

As configuracoes padrao sao para desenvolvimento local. Antes de publicar, defina DJANGO_SECRET_KEY, DJANGO_DEBUG=False e DJANGO_ALLOWED_HOSTS no ambiente, alem de configurar HTTPS e um banco de producao.
