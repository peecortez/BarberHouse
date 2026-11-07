# BarberHouse

Sistema web para gerenciamento de uma barbearia, desenvolvido com Django. Clientes podem consultar serviços e profissionais com agenda aberta, verificar horários disponíveis e acompanhar seus agendamentos. Profissionais podem gerenciar a própria agenda e atualizar o status dos atendimentos.

## Funcionalidades

- Cadastro e login de clientes e profissionais, com CPF validado (dígitos verificadores e unicidade), previsto para validação de cupons e promoções.
- Cadastro de serviços pelo painel administrativo do Django.
- Consulta de horários disponíveis por serviço, profissional e data.
- Criação e acompanhamento de agendamentos.
- Notificações (login, agendamento) no canto superior direito, alinhadas à barra de navegação. Ficam 6 segundos na tela, com uma barra de progresso que pausa enquanto o mouse está em cima, e podem ser fechadas no "x".
- Visualização separada de agendamentos ativos, concluídos e cancelados.
- Identificação de quem cancelou cada agendamento.
- Confirmação, conclusão e cancelamento de atendimentos, conforme o perfil do usuário.
- Abertura e fechamento da agenda do profissional.
- Notícia de promoção com código de 15% de desconto (`BARBER15OFF` + 3 últimos dígitos do CPF), um por CPF, exibido ao cliente logado. O profissional valida o uso ao concluir o atendimento; depois disso o cliente vê "Cupom já resgatado".
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

## Fluxo de uso

1. Crie uma conta como cliente ou profissional pela página de cadastro.
2. Entre com o e-mail e a senha cadastrados.
3. Como profissional, cadastre ou solicite que um administrador cadastre serviços e gerencie os agendamentos recebidos. A agenda começa aberta e pode ser fechada na interface.
4. Como cliente, escolha um serviço, um profissional disponível, uma data e um horário para agendar.
5. Acompanhe ou cancele seus agendamentos na área correspondente.

Os horários são oferecidos em intervalos de 30 minutos entre 8h e 18h, considerando a duração do serviço e os agendamentos existentes.

## Estrutura do projeto

```text
BarberHouse/
├── agendamentos/       # Modelos, telas, formulários, rotas e arquivos estáticos
├── barbearia/          # Configurações e rotas principais do Django
├── manage.py           # Utilitário de administração do Django
└── db.sqlite3          # Banco SQLite local (criado/atualizado pelas migrações)
```

### Templates

As telas herdam de um layout comum em `agendamentos/templates/`:

- `base.html`: esqueleto de todas as páginas (viewport, fontes Geist e DM Sans, CSS, ícones e notificações).
- `base_auth.html`: login e cadastro, com o card centralizado.
- `base_app.html`: telas internas, com a barra de navegação fixa (links conforme o perfil, link ativo destacado e botão Sair).
- `_logo.html`: o logo do login, do cadastro e da abertura, incluído com `{% include '_logo.html' with tamanho='auth' %}`. Os tamanhos são `auth` e `abertura`. Com `slogan=True`, mostra também "barbearia & estilo".

O tipo do usuário logado (`cliente` ou `profissional`) e o primeiro nome dele chegam a todos os templates como `tipo_usuario` e `primeiro_nome`, pelo context processor `agendamentos/context_processors.py`. O JavaScript das telas fica em `agendamentos/static/agendamentos/menu.js`, e os estilos em `barbearia.css`.

### Identidade visual

O logo oficial (bigode, "barberhouse" e o slogan "barbearia & estilo") foi adaptado para o tema escuro:

- **Home:** o logo completo animado (`referencias/logo-barberhouse-animada.svg`) fica colado direto no `home.html`, acima da saudação.
- **Barra de navegação:** só o bigode animado (`referencias/bigode-animado.svg`), colado direto no `base_app.html`. Ele leva para o Início e fica âmbar no hover.
- **Animação dos SVGs:** a metade esquerda do bigode gira de leve a cada 2,6s, com animação SMIL nativa do SVG. Para quem ativa "reduzir movimento", o `menu.js` congela o bigode parado.
- **Cores:** os SVGs originais são escuros sobre creme. Aqui as cores vêm do CSS (`.svg-tinta`, `.svg-destaque` e `.svg-slogan`): o bigode e "barber" ficam claros, e "house" usa o âmbar da interface no lugar do ferrugem original (`#b9512a`).
- **Fonte:** o nome usa Inter 800 e o slogan Inter 400, carregadas pelo Google Fonts, como no design oficial.
- **Login, cadastro e abertura:** usam `_logo.html`. O bigode é uma máscara (`logo-bigode.png`) e o nome é texto em Inter.
- **Favicon:** `favicon.png` e `apple-touch-icon.png` mantêm as cores originais, com o bigode escuro sobre creme.

Tema escuro com um único acento âmbar (`#e2a053`), usado apenas no botão principal, no link ativo e no foco. Títulos em DM Sans peso 500, títulos de seção em Geist e botões e campos em formato de pílula. Na home, o título tem dois tons: a saudação em branco e a pergunta em cinza.

Todas as telas usam glassmorphism: uma foto em preto e branco fica ao fundo com um véu escuro, e os cards, a barra de navegação, os diálogos e as notificações são painéis de vidro translúcido com desfoque leve, borda clara, reflexo na borda superior e sombra suave. Cada tela pode ter a própria foto pelo bloco `classe_fundo` de `base_app.html`:

- `fundo-home` (poste de barbeiro, `fundo-home.jpg`): menu inicial.
- `fundo-agendamentos` (cadeira, `fundo-agendamentos.jpg`): Agendar e Meus agendamentos.
- Sem classe: a foto padrão (`fundo-barbearia.jpg`), usada também no login e no cadastro.

As cores, os raios, as fontes e a intensidade do vidro ficam em variáveis no topo de `barbearia.css` (`--cor-*`, `--raio-*`, `--fonte-*` e `--vidro-*`). Quem ativa "reduzir movimento" no sistema vê as telas sem animação e sem transição entre páginas.

## Observações

As configuracoes padrao sao para desenvolvimento local. Antes de publicar, defina DJANGO_SECRET_KEY, DJANGO_DEBUG=False e DJANGO_ALLOWED_HOSTS no ambiente, alem de configurar HTTPS e um banco de producao.
