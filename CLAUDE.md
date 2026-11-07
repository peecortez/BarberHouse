# CLAUDE.md

Contexto do projeto para o Claude Code. O README explica o que o sistema faz e como rodar; este arquivo guarda as regras de trabalho, as decisões de design e o que está pendente.

## Regras de trabalho

- **Não commitar sem pedido explícito.** Deixe as mudanças no working tree; o usuário commita quando quiser.
- **Sempre atualizar o `README.md`** quando uma mudança alterar funcionalidades, estrutura, templates ou identidade visual.
- **Perguntar antes de aplicar um conceito visual novo** (nova referência, mudança de estilo): apresentar o que se pode aproveitar e deixar o usuário escolher.
- Conversar em português.
- Trabalho visual em andamento na branch `refinamentos-visuais` (não mexer na `main`).
- A pasta `referencias/` (originais do logo, fundos, SVGs, prints) fica só local, no `.gitignore`. O que o site usa está em `agendamentos/static/`.
- Quando o usuário pedir ajuda para commitar, só passar o passo a passo: ele mesmo roda o commit e o push.

## Ambiente

- Windows. O Python não está no PATH: use `.\venv\Scripts\python.exe`.
- O repositório git é esta pasta (`BarberHouse\BarberHouse`), não a pasta de fora.
- Testes: `.\venv\Scripts\python.exe manage.py test agendamentos` (44 testes, todos passando na última vez).
- Servidor: `.\venv\Scripts\python.exe manage.py runserver`.

## Estrutura do front

- Templates herdam de `base.html` → `base_auth.html` (login/cadastro) ou `base_app.html` (telas internas, com a barra de navegação).
- `_logo.html`: logo (bigode + "barberhouse" + slogan) do login, cadastro e abertura.
- `_toasts.html`: notificações. `agendamentos/context_processors.py` entrega `tipo_usuario` e `primeiro_nome` a todos os templates.
- Todo o CSS em `agendamentos/static/agendamentos/barbearia.css` (variáveis no topo: `--cor-*`, `--raio-*`, `--fonte-*`, `--vidro-*`, `--ease-*`). Todo o JS em `menu.js`.
- CSS e JS são carregados com a tag `static_v` (cache-busting).

## Decisões de design (já aprovadas pelo usuário)

- **Tema escuro com glassmorphism em todas as telas:** foto de fundo em P&B com véu escuro; cards, barra, diálogos e notificações em vidro translúcido (blur leve de 10px, borda clara, reflexo em cima, sombra suave).
- **Um único acento: âmbar `#e2a053`**, só no botão principal, link ativo, foco e palavras de destaque.
- **Fontes:** DM Sans (texto e títulos grandes), Geist (títulos de seção), Inter 800/400 (só no logo), todas pelo Google Fonts.
- **Fotos de fundo por tela** (bloco `classe_fundo` em `base_app.html`):
  - `fundo-home.jpg` (poste de barbeiro): Home. Mantém o vermelho/azul do poste, de propósito.
  - `fundo-agendamentos.jpg` (cadeira): Agendar e Meus agendamentos.
  - `fundo-barbearia.jpg`: demais telas e login/cadastro.
- **Logo oficial adaptado ao tema escuro:** bigode e "barber" claros, "house" em âmbar (o original é ferrugem `#b9512a`).
  - Home: SVG completo animado colado direto em `home.html`.
  - Barra: só o bigode animado (SVG) em `base_app.html`.
  - Login/cadastro/abertura: `_logo.html` (bigode como máscara `logo-bigode.png` + nome em Inter).
  - Favicon mantém as cores originais (bigode escuro sobre creme).
- **Título em dois tons na Home:** "Olá, Nome." branco + "O que vamos fazer hoje?" cinza.
- **Movimento:**
  - Abertura da marca só na primeira Home após o login (flag `abertura_marca` na sessão): logo no centro sobre preto, depois a foto abre do centro para as bordas.
  - View Transitions entre páginas: o card clicado na Home vira o cabeçalho da página seguinte; a barra fica parada. Firefox só troca de página.
  - Notificações: 6s (o tempo é a barra de progresso; pausa com o mouse em cima), com botão "x".
  - Tudo respeita "reduzir movimento". Os SVGs usam SMIL, então o `menu.js` os congela nesse caso.
- Referências usadas: Dimension (base), Mercury, Tomorro, Ponder e Jason Bradley.

## Pendências (decisão do usuário)

- Cor de "house" no logo: manter âmbar ou usar o ferrugem original (uma linha no CSS: `.svg-destaque` e `.logo-nome-destaque`).
- O bigode da barra gira o tempo todo; alternativa oferecida: girar só no hover.
- O usuário ainda precisa testar no navegador real a transição card → página e a abertura (não dá para ver no headless).

## Verificação visual

- Rodar os testes e conferir capturas de tela antes de dizer que algo está pronto.
- Captura com o Edge headless: `msedge --headless=new --window-size=1440,900 --virtual-time-budget=5000 --screenshot=...`.
- Cuidados:
  - O headless tem largura mínima de ~492px. Para celular, use um `iframe` de 390px numa página wrapper.
  - Páginas abertas como `file://` não mostram `mask-image` (o bigode do `_logo.html`). Teste pelo `runserver` ou embuta a máscara como data URI.
  - O relógio virtual do headless pausa durante carregamentos. Para ver o meio de uma animação, congele com `animation-play-state: paused` e `animation-delay` negativo.
- O headless é Chromium e não reproduz o Safari do iPhone (WebKit). O usuário testa no iPhone real com `cloudflared tunnel --url http://localhost:8000`.
- Cuidados conhecidos no iOS (já tratados no CSS):
  - `input[type=date]` precisa de `appearance: none` e `min-width: 0`, senão vaza do card e fica mais alto.
  - Campos com fonte menor que 16px fazem o Safari dar zoom ao tocar; no celular os campos usam 16px.
