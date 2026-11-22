# Avaliações na Home do cliente — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Na Home do cliente, abaixo dos cards do menu, mostrar as avaliações com comentário no estilo "Animated Testimonials" (pilha de cards + texto palavra por palavra + setas).

**Architecture:** A view `home` passa as avaliações já prontas. Um partial (`_avaliacoes_destaque.html`) gera todos os cards no HTML, e o primeiro já vem ativo. O `menu.js` só troca o card ativo e anima. Estilos no fim da seção da Home em `barbearia.css`.

**Tech Stack:** Django 5 (templates), CSS puro, JS puro. Sem dependências novas.

**Spec:** `docs/superpowers/specs/2026-11-21-avaliacoes-home-design.md`

## Global Constraints

- Regras do `CLAUDE.md`: **não commitar** (o usuário commita); atualizar o README; conversar em português.
- Trabalhar na branch nova `avaliacoes-na-home`, criada a partir da `main` (`git checkout -b avaliacoes-na-home`). A mudança pendente no `CLAUDE.md` vai junto.
- Só na Home do **cliente**. As 8 mais recentes (`criado_em` desc) com comentário não vazio, de qualquer nota.
- Só o primeiro nome do cliente. Sem avaliações → a seção não é renderizada.
- Título: "O que dizem nossos clientes". Linha de apoio: "<Serviço> com <Profissional>".
- Card da pilha: vidro (`--vidro-*`) com a inicial do cliente grande e `_estrelas.html` embaixo.
- Tempos: pilha 0,4s ease-in-out, pulo y 0 → -80px → 0, origem embaixo, giro aleatório de -10° a 10° nos de trás, escala 0,95 e opacidade 0,7 nos de trás. Texto: blur 10px → 0, 0,2s por palavra, 0,02s entre palavras. Setas: ícone gira no hover, ← `rotate(12deg)` e → `rotate(-12deg)`, em 0,3s.
- Sem autoplay. `prefers-reduced-motion: reduce` → troca instantânea, sem giro/pulo/palavra por palavra (o `menu.js` já tem `reduzirMovimento`).
- Acento âmbar só nas estrelas e no foco. Fontes do projeto (DM Sans / Geist). Celular (≤600px): pilha em cima, texto embaixo.
- Rodar testes com `.\venv\Scripts\python.exe manage.py test agendamentos` na pasta do `manage.py`.

## Review Focus

1. **Comentário só com espaços** (`"   "`) não pode virar card vazio → o form já faz strip; o teste do Task 1 cobre `comentario=""`.
2. **Comentário longo (500 caracteres)** não pode estourar o card nem empurrar as setas para fora no celular → conferir na captura de 390px (Task 2).
3. **Uma avaliação só** → a pilha mostra um card, e as setas ficam escondidas ou desativadas, sem erro no console (Task 2).
4. **Comentário com HTML** (`<script>`) tem que sair escapado: o JS anima as palavras via `textContent`, nunca `innerHTML` (teste no Task 1 e revisão no Task 2).
5. **Cliente sem nome / nome com espaços extras** → a inicial e o primeiro nome não podem quebrar (`Cliente.primeiro_nome` devolve "" e a inicial cai para "?"). Teste no Task 1.

---

### Task 1: Avaliações na view `home` e o partial

**Files:**
- Modify: `agendamentos/models.py` (property em `Cliente`)
- Modify: `agendamentos/context_processors.py` (reusar a property)
- Modify: `agendamentos/views.py:160-167` (`home`)
- Create: `agendamentos/templates/_avaliacoes_destaque.html`
- Modify: `agendamentos/templates/home.html` (incluir o partial depois de `.opcoes-menu-inicial`, só para cliente)
- Test: `agendamentos/tests.py` (classe nova `AvaliacoesNaHomeTests(BaseComPerfis)`)

**Interfaces:**
- Produces: `Cliente.primeiro_nome -> str` (property; `""` se não houver nome).
- Produces: `_avaliacoes_em_destaque(limite: int = 8) -> QuerySet[Avaliacao]` em `views.py`, com `select_related('agendamento__cliente', 'agendamento__profissional', 'agendamento__servico')`, `exclude(comentario='')`, ordem `-criado_em`.
- Produces: contexto `avaliacoes_destaque` na `home` (só para cliente; profissional não recebe a chave).
- Produces (markup para o Task 2): `<section class="avaliacoes-destaque" data-avaliacoes aria-labelledby="tituloAvaliacoes">` com:
  - `<h2 id="tituloAvaliacoes">O que dizem nossos clientes</h2>`;
  - `.avaliacoes-pilha` com um `.avaliacao-card` por avaliação (inicial em `.avaliacao-card-inicial` + `_estrelas.html`), `aria-hidden="true"`;
  - `.avaliacoes-textos` com um `<figure class="avaliacao-texto">` por avaliação (`<figcaption>` com o nome em `.avaliacao-nome`, o apoio em `.avaliacao-apoio` e `<blockquote class="avaliacao-comentario-destaque">`);
  - o 1º card e o 1º texto com a classe `ativo`, e os outros textos com `hidden`;
  - `.avaliacoes-setas` com `<button type="button" data-avaliacao-anterior aria-label="Avaliação anterior">` e `data-avaliacao-proxima` ("Próxima avaliação"), com os ícones `fa-arrow-left` e `fa-arrow-right`. Só renderizar as setas se houver mais de uma avaliação.

- [ ] **Step 1: Escrever os testes que falham**

Helper na classe: `avaliar(self, comentario, nota=5, nome_cliente="Lucas Pereira")`, que cria um Cliente novo, um Agendamento CONCLUIDO com `self.prof`/`self.servico` e uma `Avaliacao`.

```python
def test_cliente_ve_avaliacoes_com_comentario_na_home(self):
    self.avaliar("Corte impecável")
    self.logar("cli@x.com")
    resp = self.client.get(reverse("home"))
    self.assertContains(resp, "O que dizem nossos clientes")
    self.assertContains(resp, "Corte impecável")
    self.assertContains(resp, "Lucas")
    self.assertNotContains(resp, "Pereira")          # só o primeiro nome
    self.assertContains(resp, "Corte com Barbeiro")

def test_sem_comentario_nao_aparece_e_secao_some(self):
    self.avaliar("")
    self.logar("cli@x.com")
    self.assertNotContains(self.client.get(reverse("home")), "O que dizem nossos clientes")

def test_profissional_nao_ve_a_secao(self):
    self.avaliar("Muito bom")
    self.logar("bar@x.com")
    self.assertNotContains(self.client.get(reverse("home")), "O que dizem nossos clientes")

def test_mostra_as_8_mais_recentes(self):
    for i in range(10):
        self.avaliar(f"comentario numero {i:02d}", nome_cliente=f"C{i}")
    # forçar criado_em crescente com update() se auto_now_add empatar
    self.logar("cli@x.com")
    html = self.client.get(reverse("home")).content.decode()
    self.assertIn("comentario numero 09", html)
    self.assertNotIn("comentario numero 01", html)
    self.assertEqual(html.count('class="avaliacao-card'), 8)

def test_comentario_com_html_sai_escapado(self):
    self.avaliar("<script>alert(1)</script>")
    self.logar("cli@x.com")
    resp = self.client.get(reverse("home"))
    self.assertNotContains(resp, "<script>alert(1)</script>")
    self.assertContains(resp, "&lt;script&gt;")

def test_primeiro_nome_de_cliente_sem_nome(self):
    self.assertEqual(Cliente(nome="  ").primeiro_nome, "")
    self.assertEqual(Cliente(nome=" Ana  Clara ").primeiro_nome, "Ana")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\venv\Scripts\python.exe manage.py test agendamentos.tests.AvaliacoesNaHomeTests`
Expected: FAIL (título não encontrado / `primeiro_nome` não existe).

- [ ] **Step 3: Implementar**

`Cliente.primeiro_nome`; o `context_processors.py` passa a usar a mesma lógica (`nome.split()[0]`). Para não duplicar, extraia uma função `primeiro_nome(nome: str) -> str` em `models.py` e use-a nos dois lugares. `_avaliacoes_em_destaque` e o contexto da `home`. O partial segue o markup descrito em Interfaces. Inicial: `{{ cliente.primeiro_nome|first|upper|default:"?" }}`.

- [ ] **Step 4: Rodar a suíte inteira**

Run: `.\venv\Scripts\python.exe manage.py test agendamentos`
Expected: OK (81 + 6 testes).

- [ ] **Step 5: Não commitar** (regra do projeto).

---

### Task 2: Visual e animação (CSS + JS)

**Files:**
- Modify: `agendamentos/static/agendamentos/barbearia.css` (bloco novo "Avaliações na Home", depois da seção do menu inicial; ajustes em `@media (max-width: 600px)` e `@media (prefers-reduced-motion: reduce)`)
- Modify: `agendamentos/static/agendamentos/menu.js` (função `ligarAvaliacoesDestaque()` chamada no `DOMContentLoaded`)

**Interfaces:**
- Consumes: o markup do Task 1 (`[data-avaliacoes]`, `.avaliacao-card`, `.avaliacao-texto`, `.ativo`, `hidden`, `[data-avaliacao-anterior]`, `[data-avaliacao-proxima]`, `.avaliacao-comentario-destaque`).
- Produces: nada para outros tasks.

- [ ] **Step 1: CSS**
  - Layout: grid de 2 colunas (≥601px) com `gap` grande, e 1 coluna no celular.
  - `.avaliacoes-pilha`: `position: relative`, altura fixa (~320px desktop / ~260px celular), `perspective: 1000px`.
  - `.avaliacao-card`: `position: absolute; inset: 0; transform-origin: bottom`, vidro, `border-radius: var(--raio-card)`. A inicial em `--fonte-titulo`, ~120px, `--cor-titulo`. Transição de `transform`/`opacity` em 0,4s ease-in-out. Giro, escala, opacidade e `z-index` vêm de custom properties que o JS define (`--giro`, `--camada`).
  - `.avaliacao-card.ativo`: escala 1, opacidade 1, giro 0 e `animation: avaliacao-pulo 0.4s ease-in-out` (keyframes 0 → -80px → 0).
  - Palavras: `.avaliacao-palavra { display: inline-block; animation: avaliacao-palavra 0.2s ease-in-out backwards; animation-delay: calc(var(--i) * 0.02s) }`, com keyframes de `filter: blur(10px); opacity: 0; translateY(5px)` até o estado normal.
  - Setas: botões redondos de vidro (~40px). O ícone gira 12° no hover (← `rotate(12deg)`, → `rotate(-12deg)`) em 0,3s. `:focus-visible` com o anel âmbar do projeto.
  - Comentário: `overflow-wrap: anywhere`.
  - `prefers-reduced-motion: reduce`: sem keyframes de pulo e de palavra, e `--giro` zerado.

- [ ] **Step 2: JS `ligarAvaliacoesDestaque()`**
  - Se não houver `[data-avaliacoes]`, retorna.
  - Sorteia um `--giro` (inteiro de -10 a 10, em deg) para cada card de trás a cada troca, como o `randomRotateY` da referência.
  - `mostrar(indice)`: tira e põe `ativo` nos cards e textos (os textos inativos recebem `hidden`), atualiza `--camada` (o ativo fica em 40, os outros em `total + 2 - i`) e reinicia o pulo (tirar a classe, forçar reflow, pôr de volta).
  - Fatiar o comentário: quebra em palavras e cria um `<span class="avaliacao-palavra" style="--i:n">` por palavra **com `textContent`**, só se `!reduzirMovimento.matches`.
  - Setas: anterior `(i - 1 + total) % total`, próxima `(i + 1) % total`. Teclas ← → quando o foco está numa das setas.
  - Com 1 avaliação: não há setas (Task 1), e o JS não pode dar erro.

- [ ] **Step 3: Verificação visual**
  - Criar avaliações locais (ou rodar o `resetar_demo` depois do Task 3), subir o `runserver` e capturar com o Edge headless (`--window-size=1440,900`) a Home logada como cliente, rolada até a seção. Para celular, usar uma página wrapper com `iframe` de 390px (ver o `CLAUDE.md`).
  - Conferir: pilha girada atrás, ativo reto, texto legível, setas visíveis, comentário de 500 caracteres sem estourar no celular.
  - Console sem erros.

- [ ] **Step 4: Rodar a suíte** (nada pode quebrar; o `VersaoDoStaticTest` cobre o cache-busting).

- [ ] **Step 5: Não commitar.**

---

### Task 3: Avaliações de exemplo no `resetar_demo`

**Files:**
- Modify: `agendamentos/management/commands/resetar_demo.py`
- Test: `agendamentos/tests.py` (classe nova `ResetarDemoTests(TestCase)`)

**Interfaces:**
- Produces: a constante `AVALIACOES_DEMO` (lista de dicts `cliente`, `profissional` (e-mail de um dos `PROFISSIONAIS_DEMO`), `nota`, `comentario`), com 5 itens, notas 4 e 5 e comentários curtos e naturais em PT-BR.

- [ ] **Step 1: Testes que falham**

```python
def test_cria_avaliacoes_de_exemplo_quando_ha_servico(self):
    Servico.objects.create(nome="Corte", duracao_minutos=30, preco=40)
    call_command("resetar_demo", stdout=StringIO())
    self.assertEqual(Avaliacao.objects.exclude(comentario="").count(), 5)
    self.assertTrue(all(a.agendamento.status == Agendamento.Status.CONCLUIDO
                        for a in Avaliacao.objects.all()))
    self.assertEqual(Profissional.objects.count(), 4)
    self.assertEqual(EmailEnviado.objects.count(), 0)   # não manda e-mail

def test_sem_servico_nao_cria_avaliacoes(self):
    call_command("resetar_demo", stdout=StringIO())
    self.assertFalse(Avaliacao.objects.exists())
```

- [ ] **Step 2: Rodar e ver falhar.**

- [ ] **Step 3: Implementar**
  - Depois de criar os profissionais, se existir algum `Servico`, criar para cada item um `User` (ativo, `SENHA_DEMO`), um `Cliente` (e-mail `<nome>@cliente.demo`, sem CPF), um `Agendamento` CONCLUIDO no passado (entre 1 e 20 dias atrás, às 10h) e a `Avaliacao`.
  - Criar com o ORM, sem passar por `emails.enviar`.
  - Imprimir "N avaliações de exemplo criadas", ou um aviso de que não há serviços cadastrados.
  - Atualizar o `help` do comando.

- [ ] **Step 4: Rodar a suíte inteira.** Expected: OK.

- [ ] **Step 5: Não commitar.**

---

### Task 4: Documentação e verificação final

**Files:**
- Modify: `README.md` (Funcionalidades: avaliações na Home; Templates: `_avaliacoes_destaque.html`; `resetar_demo`: clientes e avaliações de exemplo, com e-mails `@cliente.demo` e senha `barber123`)
- Modify: `CLAUDE.md` (contagem de testes; o partial na "Estrutura do front")

- [ ] **Step 1: Atualizar o README e o CLAUDE.md.**
- [ ] **Step 2: Suíte inteira verde, com a contagem final anotada no CLAUDE.md.**
- [ ] **Step 3: Capturas finais (desktop e celular) conferidas.**
- [ ] **Step 4: Atualizar a nota `Projetos/BarberHouse.md` no Cérebro** (o estado e a funcionalidade nova).
- [ ] **Step 5: Não commitar.** Passar ao usuário o passo a passo de commit/PR.
