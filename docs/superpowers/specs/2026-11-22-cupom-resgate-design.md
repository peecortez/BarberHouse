# Cupom só vale depois que o cliente resgata — design curto

**Pedido:** o profissional só pode aplicar o cupom de 15% se o cliente tiver resgatado o cupom (clicado em "Pegue seu cupom aqui" em Notícias). Sem resgate, o cupom não pode ser aplicado.

**Hoje:** o clique em "Pegue seu cupom aqui" só revela o código na tela (JS) e não grava nada. O campo `Cliente.cupom_resgatado_em` é gravado quando o **profissional** aplica o cupom, ou seja, hoje "resgatado" significa "usado".

## Decisões (aprovadas pelo usuário em 2026-11-22)

- O clique do cliente passa a ser gravado no servidor (resgate).
- A opção "O cliente aplicou o cupom de 15%" no diálogo de concluir só aparece para o profissional se o cliente resgatou e ainda não usou.
- O servidor também recusa aplicar sem resgate (409), mesmo com a tela burlada.
- Depois de usado, o cliente vê "Cupom já usado".

## Como (decisões do Claude)

- **Dois campos com nomes que dizem o que são:** `cupom_resgatado_em` passa a ser o clique do cliente; o antigo vira `cupom_usado_em` (`RenameField`). A migração copia `cupom_usado_em` para o novo `cupom_resgatado_em` em quem já usou, porque quem usou necessariamente pegou.
- Properties: `cupom_resgatado`, `cupom_usado` e `cupom_disponivel` (CPF + resgatado + não usado), que continua controlando o checkbox do profissional.
- **Rota nova** `POST /noticias/resgatar-cupom/` (`resgatar_cupom`): só cliente com CPF; idempotente (um segundo clique não muda a data). Por `fetch`, responde JSON com o código; sem JS, o form redireciona de volta a Notícias.
- **Notícias:** o código só vai para o HTML depois do resgate (antes, a área fica vazia e o JS a preenche com a resposta). Se já resgatou, a área do código aparece direto, sem botão.
- **Aplicar:** o `update` atômico exige `cupom_resgatado_em` preenchido e `cupom_usado_em` vazio. A mensagem diz o motivo: "O cliente ainda não resgatou o cupom" ou "Cupom já usado".

## Abordagens consideradas

1. **Gravar o resgate no servidor (escolhida):** a regra vale de verdade e o profissional vê só quando pode aplicar.
2. Guardar o resgate só no navegador (`localStorage`): o profissional não teria como saber; descartada.
3. Manter um campo só com três estados (texto): menos colunas, mas confunde datas e estados; descartada.

## Fora do escopo

- Prazo de validade do cupom e desfazer o resgate.
