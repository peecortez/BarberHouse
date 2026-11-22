# Página "Sobre" — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trocar "Mais" por "Sobre", com história, galeria "Nosso espaço" e contatos fictícios.

**Architecture:** página estática (`sobre.html` herdando `base_app.html`), view simples, fotos em `static/agendamentos/sobre/`. Estilos num bloco novo do `barbearia.css`.

**Tech Stack:** Django 5, CSS puro. Recorte das fotos com .NET `System.Drawing` (PowerShell), sem dependência nova no projeto.

**Spec:** `docs/superpowers/specs/2026-11-22-pagina-sobre-design.md`

## Global Constraints

- Regras do `CLAUDE.md`: não commitar, atualizar README, português.
- Textos fixos: "Sobre"; "Desde 2015, cuidando do seu estilo"; "Nossa história"; "Nosso espaço"; "Fale com a gente"; "Onde estamos"; "(11) 90000-0000"; "@barberhouse.oficial"; "@barberhouse"; "Seg–Sáb, 8h às 18h"; card da Home "Nossa história, espaço e contatos." com `fa-store`.
- Contatos sem `href`. Fotos com `alt` descritivo, `loading="lazy"` (menos a primeira), `width`/`height`.
- CSS e acento: âmbar só em destaque/foco; vidro com `--vidro-*`.

## Review Focus

1. **Link antigo `/mais/`** → 404 (a rota sai); nenhum template pode ainda usar `{% url 'mais' %}` (quebraria a página inteira). Teste no Task 2.
2. **Celular 390px** → galeria em uma coluna, história sem a foto espremida, sem rolagem horizontal. Captura no Task 3.
3. **Foto faltando no static** → imagem quebrada silenciosa. Teste que as 4 existem via `finders.find` no Task 2.
4. **Peso da página** → cada foto ≤ 300 KB. Teste no Task 2.
5. **Visitante sem login** → a página abre (200), como o "Mais". Teste no Task 2.

---

### Task 1: Fotos

- [ ] Copiar os 2 originais para `referencias/sobre/`.
- [ ] Recortar a grade nos 4 quadros (detectar as faixas brancas), descartar o quadro de cima à esquerda (repetido pela foto avulsa) e salvar em JPEG (qualidade ~80, maior lado ≤ 1200px): `sobre/fachada.jpg`, `sobre/cadeira-logo.jpg` (foto avulsa), `sobre/cadeira-classica.jpg`, `sobre/recepcao.jpg`.
- [ ] Conferir visualmente cada recorte (sem borda branca).

### Task 2: Rota, view, template e navegação (TDD)

**Files:** `views.py` (`sobre` no lugar de `mais`), `urls.py`, `templates/sobre.html` (novo), `templates/mais.html` (apagar), `base_app.html`, `home.html`, `tests.py` (classe `PaginaSobreTests(BaseComPerfis)` + trocar `"mais"`/`"/mais/"` por `"sobre"`/`"/sobre/"` nos 3 testes existentes).

- [ ] Testes que falham: `test_sobre_abre_sem_login` (200, contém "Nossa história", "Nosso espaço", "(11) 90000-0000", "@barberhouse.oficial"); `test_contatos_sem_link` (nenhum `href` com "instagram", "wa.me", "tiktok"); `test_quatro_fotos_com_alt` (4 `<img` dentro de `.sobre-galeria`, todas com `alt="` não vazio); `test_fotos_existem_e_sao_leves` (`finders.find` para as 4; `getsize ≤ 300_000`); `test_barra_e_home_levam_a_sobre` (logado como cliente, `href="/sobre/"` e "Sobre"; sem `href="/mais/"`); `test_mais_saiu` (`/mais/` → 404).
- [ ] Rodar e ver falhar.
- [ ] Implementar.
- [ ] Suíte inteira verde.

### Task 3: Visual, docs

- [ ] CSS do bloco "Página Sobre" (história em 2 colunas ≥ 801px; galeria 2×2 ≥ 601px, 1 coluna abaixo; fotos `aspect-ratio` fixo com `object-fit: cover`, véu escuro nas bordas por `box-shadow: inset` ou gradiente; contatos em 2 cards de vidro).
- [ ] Capturas desktop (1440) e celular (390, wrapper com iframe); sem rolagem horizontal.
- [ ] README (funcionalidades, templates, estrutura de static) e `CLAUDE.md` (contagem de testes; `sobre.html`).
- [ ] Nota do Cérebro. Não commitar.
