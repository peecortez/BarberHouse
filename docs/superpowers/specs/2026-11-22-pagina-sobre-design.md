# Página "Sobre" no lugar de "Mais" — design curto

**Pedido:** trocar o botão "Mais" por "Sobre", com uma história fictícia da barbearia, redes sociais e WhatsApp fictícios e "Nosso espaço" com fotos. O usuário gerou as fotos (uma grade 2×2 e uma foto avulsa). Aprovado em 2026-11-22.

## Decisões aprovadas

- "Mais" vira "Sobre" na barra e no card da Home (ícone `fa-store`, descrição "Nossa história, espaço e contatos."). Rota `/sobre/` (`name='sobre'`); `/mais/` e `mais.html` saem. Página aberta a todos, como era o "Mais".
- Cabeçalho: título "Sobre", subtítulo "Desde 2015, cuidando do seu estilo" (um pôster nas fotos diz "EST. 2015").
- **Nossa história:** 3 parágrafos curtos (começo em 2015 com uma cadeira, crescimento, o que a casa valoriza hoje), ao lado da foto da fachada.
- **Nosso espaço:** 4 fotos coloridas, cantos arredondados, bordas escurecidas e legenda curta: cadeira com o logo (a foto avulsa, que é a mesma cena da grade em resolução maior), cadeira clássica, recepção, fachada. Celular: uma coluna.
- **Fale com a gente / Onde estamos:** WhatsApp (11) 90000-0000, Instagram @barberhouse.oficial, TikTok @barberhouse, endereço fictício, Seg–Sáb das 8h às 18h (horário da agenda). Contatos **só em texto com ícone, sem link** (contas reais com esses nomes podem existir).
- As duas primeiras fotos de referência (madeira/verde e preto/LED) ficam de fora: outro estilo, sem a marca.
- Fotos recortadas e comprimidas (~200 KB cada) em `agendamentos/static/agendamentos/sobre/`; originais em `referencias/` (fora do Git).

## Ajustes feitos na implementação (decisões do Claude)

- A fachada aparece só ao lado da história; a galeria ficou com as outras 3 fotos lado a lado (no esboço a fachada aparecia duas vezes).
- A etiqueta da história virou "Barbearia & estilo" (o slogan), porque "Desde 2015" já está no subtítulo.
- O corte das fotos preserva o alto (`object-position: 50% 12%`), onde ficam os letreiros; no celular as fotos ficam em 4:3.

## Abordagens consideradas

1. **Página estática no template, sem model (escolhida):** o conteúdo é fixo e fictício; nada para o admin editar.
2. Conteúdo em model editável no admin: flexível, mas YAGNI para um texto fixo.
3. Galeria com lightbox (ampliar ao clicar): mais JS e mais estados; fica de fora por ora.

## Deixado para o construtor

- O texto exato da história e das legendas, dentro do tom do site (curto, sem exagero).
- O endereço fictício.
