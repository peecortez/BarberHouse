# Avaliações na Home do cliente — design curto

## Intenção
Na Home do cliente, rolando para baixo depois dos cards do menu, uma seção mostra as avaliações de outros clientes, para quem vai agendar ver o que acharam dos atendimentos. Referência visual: "Animated Testimonials" (Aceternity UI).

## Abordagens
- **Recriar em JS + CSS puros (escolhida).** Segue a estrutura do projeto (templates Django, `barbearia.css`, `menu.js`), sem build e sem dependências novas.
- React + Tailwind + Motion por CDN: descartada. Deixaria a Home pesada, o Tailwind entraria em conflito com o CSS atual e o projeto não tem etapa de build.
- Grade simples de cards: descartada porque não segue a referência pedida.

## Decidido com o usuário
- Só na Home do **cliente**.
- Na pilha, cada card é de **vidro com a inicial grande do cliente e as estrelas** (sem fotos).

## Comportamento (da referência, adaptado)
- **Esquerda:** pilha de cards. O ativo fica na frente, reto e com opacidade 1. Os outros ficam atrás, com escala 0,95, opacidade 0,7 e giro aleatório entre -10° e 10°. Na troca, o ativo dá um pulo (y 0 → -80px → 0) em 0,4s ease-in-out, com origem embaixo.
- **Direita:** primeiro nome do cliente, "Serviço com Profissional", estrelas e comentário. O comentário entra palavra por palavra, de blur 10px até nítido (0,2s cada, 0,02s entre palavras).
- **Setas ← →** redondas em vidro, que giram 12° no hover. Também funcionam pelo teclado.
- Sem autoplay (o padrão da referência).
- **Reduzir movimento:** a troca é instantânea, sem giro, sem pulo e sem palavra por palavra.
- **Celular:** a pilha fica em cima e o texto embaixo.

## Calls do Claude (o usuário pode corrigir)
- Entram as **8 avaliações mais recentes que têm comentário**, de qualquer nota. Avaliações sem comentário não entram.
- **Privacidade:** só o primeiro nome do cliente.
- Sem avaliações com comentário, a seção não aparece.
- **Título da seção:** "O que dizem nossos clientes".
- O `resetar_demo` passa a criar alguns clientes, atendimentos concluídos e avaliações de exemplo, para a seção não ficar vazia na apresentação.
- Tema só escuro com glassmorphism, âmbar só nas estrelas e no foco, fontes DM Sans e Geist.
- Testes: a Home do cliente mostra a seção com as avaliações certas, e a Home do profissional não mostra.
- Atualizar o README (funcionalidades, templates e `resetar_demo`).

## Fora do escopo
- Fotos de clientes ou de profissionais.
- Página com todas as avaliações.
