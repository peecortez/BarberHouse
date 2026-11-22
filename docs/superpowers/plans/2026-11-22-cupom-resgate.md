# Cupom só vale depois do resgate — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o cliente resgata o cupom em Notícias (gravado no servidor), e o profissional só consegue aplicar um cupom resgatado e ainda não usado.

**Architecture:** dois campos de data em `Cliente` (`cupom_resgatado_em` = clique do cliente; `cupom_usado_em` = aplicado pelo profissional). Uma rota POST nova grava o resgate; `atualizar_status` passa a exigir o resgate no `update` atômico.

**Tech Stack:** Django 5, SQLite, JS puro (`menu.js`). Sem dependências novas.

**Spec:** `docs/superpowers/specs/2026-11-22-cupom-resgate-design.md`

## Global Constraints

- Regras do `CLAUDE.md`: **não commitar** (o usuário commita), atualizar o README, conversar em português.
- Branch atual `avaliacoes-na-home` (o usuário decide depois se separa).
- Textos: botão "Pegue seu cupom aqui"; estado final "Cupom já usado"; erros 409 "O cliente ainda não resgatou o cupom" e "Cupom já usado".
- Testes: `.\venv\Scripts\python.exe manage.py test agendamentos`.

## Review Focus

1. **Profissional tenta aplicar sem resgate** (tela antiga aberta ou requisição forjada) → 409, agendamento continua AGENDADO e `cupom_usado_em` vazio. Teste no Task 1.
2. **Cliente clica duas vezes / recarrega** → resgate idempotente, a data do primeiro clique não muda. Teste no Task 1.
3. **Profissional ou anônimo chamando `resgatar_cupom`** → 403 / redireciona ao login, nada gravado. Teste no Task 1.
4. **Cliente sem CPF chamando `resgatar_cupom`** → 400, nada gravado. Teste no Task 1.
5. **Cupom usado antes da migração** → continua aparecendo como usado (a migração copia a data para `cupom_resgatado_em`). Conferido rodando a migração no banco local (Task 1, Step 6).

---

### Task 1: Resgate no servidor e aplicação só com resgate

**Files:**
- Modify: `agendamentos/models.py` (`Cliente`)
- Create: `agendamentos/migrations/0008_cupom_usado.py`
- Modify: `agendamentos/views.py` (`atualizar_status`, nova `resgatar_cupom`)
- Modify: `agendamentos/urls.py` (`path('noticias/resgatar-cupom/', views.resgatar_cupom, name='resgatar_cupom')`)
- Modify: `agendamentos/templates/noticias.html`
- Modify: `agendamentos/static/agendamentos/menu.js` (bloco "Noticias: revelar e copiar o cupom")
- Test: `agendamentos/tests.py` (`ResgateCupomTests`)

**Interfaces:**
- Produces: `Cliente.cupom_resgatado_em`, `Cliente.cupom_usado_em` (DateTimeField null/blank); properties `cupom_resgatado`, `cupom_usado`, `cupom_disponivel` (`bool(cpf) and resgatado and not usado`).
- Produces: `POST resgatar_cupom` → com header `X-Requested-With: fetch`: JSON `{"codigo": "BARBER15OFF725"}`; sem o header: redirect para `noticias`.

- [ ] **Step 1: Testes que falham** (em `ResgateCupomTests`; `concluir` e `agendamento` já existem; novo helper `resgatar(self)` que loga o cliente e faz o POST com o header)

```python
def test_resgatar_grava_e_devolve_codigo(self):
    resp = self.resgatar()
    self.assertEqual(resp.json()["codigo"], "BARBER15OFF725")
    self.cliente.refresh_from_db()
    self.assertTrue(self.cliente.cupom_resgatado)
    self.assertFalse(self.cliente.cupom_usado)

def test_resgatar_duas_vezes_mantem_a_primeira_data(self): ...
    # assertEqual(primeira, segunda) de cupom_resgatado_em

def test_profissional_e_anonimo_nao_resgatam(self): ...
    # profissional logado -> 403; anônimo -> 302 para o login; nada gravado

def test_cliente_sem_cpf_nao_resgata(self): ...   # 400

def test_aplicar_sem_resgate_e_recusado(self):
    ag = self.agendamento()
    resp = self.concluir(ag, cupom=True)
    self.assertEqual(resp.status_code, 409)
    self.assertEqual(resp.json()["error"], "O cliente ainda não resgatou o cupom")
    ag.refresh_from_db()
    self.assertEqual(ag.status, Agendamento.Status.AGENDADO)

def test_checkbox_do_profissional_so_aparece_com_resgate(self): ...
    # gerenciar_agenda logado como profissional: sem resgate, sem "data-cupom-disponivel"; depois de resgatar, com ele

def test_noticias_antes_e_depois_do_resgate(self): ...
    # antes: "Pegue seu cupom aqui" e sem "BARBER15OFF725"; depois: o código, sem o botão
```

Ajustar os existentes: `test_concluir_com_cupom_resgata_e_bloqueia_reuso` → resgatar antes, conferir `cupom_usado` e o 409 "Cupom já usado" no reuso; `test_concluir_sem_cupom_nao_resgata` e `test_cliente_nao_pode_resgatar_o_proprio_cupom` → `cupom_usado`; `test_noticias_mostra_cupom_ja_resgatado` → preencher `cupom_usado_em` e esperar "Cupom já usado".

- [ ] **Step 2: Rodar e ver falhar.** `.\venv\Scripts\python.exe manage.py test agendamentos.tests.ResgateCupomTests` → FAIL.

- [ ] **Step 3: Model + migração.** Migração na ordem: `RenameField(cupom_resgatado_em → cupom_usado_em)`, `AddField(cupom_resgatado_em)`, `RunPython` que faz `Cliente.objects.filter(cupom_usado_em__isnull=False).update(cupom_resgatado_em=F('cupom_usado_em'))` (reverso: noop).

- [ ] **Step 4: Views.**
  - `resgatar_cupom`: `@login_required`, `@require_POST`; sem `cliente` → 403; sem CPF → 400; `filter(pk=…, cupom_resgatado_em__isnull=True).update(cupom_resgatado_em=now)`.
  - `atualizar_status`: o `update` passa a filtrar `cupom_resgatado_em__isnull=False, cupom_usado_em__isnull=True` e grava `cupom_usado_em`; se não atualizou, recarrega o cliente para escolher a mensagem (não resgatou / já usado).

- [ ] **Step 5: Template + JS.**
  - `noticias.html`: usado → botão desativado "Cupom já usado"; resgatado → área do código visível (com "Copiar código"); com CPF → `<form method="post" action="{% url 'resgatar_cupom' %}">` com o botão `#botaoCupom` e a área escondida com `#codigoCupom` vazio.
  - `menu.js`: o clique (submit) faz `fetch` POST com CSRF e `X-Requested-With: fetch`, coloca `codigo` no `#codigoCupom` via `textContent` e revela como hoje. Se falhar, mostra o toast de erro e não revela.

- [ ] **Step 6: Suíte inteira verde + `migrate` no banco local** (`.\venv\Scripts\python.exe manage.py migrate`) sem erro.

- [ ] **Step 7: README** (linha da promoção: o cliente resgata em Notícias, o profissional só aplica cupom resgatado) e contagem de testes no `CLAUDE.md`.

- [ ] **Step 8: Não commitar.**
