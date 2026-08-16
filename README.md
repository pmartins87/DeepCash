# DeepCash

DeepCash é o projeto de IA para **No-Limit Hold'em Cash Game 6-max**, com foco em obter a maior força prática possível dentro de um orçamento computacional realista: **um Ryzen 9 trabalhando continuamente por aproximadamente três meses**, sem assumir cluster, GPU de datacenter ou memória absurda.

## Princípio central

O objetivo não é fingir que o jogo completo será resolvido exatamente. 6-max cash NLHE é grande demais para isso no nosso orçamento.

O objetivo é:

> **usar correção matemática, invariâncias por construção, abstrações medidas, treino eficiente, subgame resolving e exploração segura para extrair o máximo de força por CPU-hora.**

Toda capacidade economizada por não reaprender equivalências triviais deve voltar para aquilo que realmente aumenta força estratégica: mais estados, melhor action abstraction, melhor representação, mais amostras ou resolving mais profundo.

## O que será reaproveitado dos projetos anteriores

DeepCash nasce depois de DeepKK/AoF, SpinCore e DeepSix. O que é reutilizado é o conhecimento de engenharia e os princípios validados, não cópia cega de soluções específicas de outra modalidade:

- **AoF / DeepKK:** baseline + camada de exploração; identificação persistente de oponentes; shrinkage; fallback seguro; auditoria de dados; separação entre estratégia matemática e runtime operacional.
- **SpinCore:** motor exato antes da rede; encoder auditável; Deep CFR; determinismo, checkpoint/resume, held-out validation, invariâncias estruturais e gates antes do treino longo.
- **DeepSix:** action/state abstraction como problema empírico; exact best-response em microgames onde for possível; canonicalização de naipes/cartas/assentos; benchmark por ganho estratégico por CPU-hora; observe/replay-first no runtime.

## Hipótese arquitetural inicial

A linha principal é híbrida:

1. **Core exato 52-card NLHE 2–6 jogadores** — regras, side pots, rake configurável, ações legais, showdown, replay e invariâncias.
2. **Blueprint abstrato** — action abstraction pequena o bastante para ser treinável, mas escolhida por benchmark e não por intuição.
3. **Representação estratégica rica** — geometria exata de pot/call/stack/SPR + histórico actor-aware + features de mão/board/range; compressão apenas onde comprar força por custo.
4. **Solver escalável** — CFR+/MCCFR/Deep CFR comparados sob oracles comuns em jogos menores; produção escolhida por evidência no Ryzen.
5. **Street decomposition e resolving** — river/turn primeiro, depois flop e integração multi-street; subgames locais devem aproveitar mais detalhe do que o blueprint global quando o orçamento permitir.
6. **Exploração segura** — modelo por jogador e pool, com shrinkage/intervalos de confiança, políticas exploratórias limitadas e fallback automático para a estratégia-base quando a evidência for fraca ou o estado não casar exatamente.
7. **OpenHoldemCash** — fork/runtime próprio para cash 6-max, sem depender de fórmulas AoF. Primeiro observa/reconstrói; autoplayer só entra depois dos gates estratégicos e operacionais.

## O que não será congelado cedo demais

Ainda não estão congelados:

- site/economia autoritativos (rake, cap, rounding, jackpot/promoções);
- stack efetivo alvo e política para mesas deep/short;
- conjunto final de bet sizes por street e por geometria;
- algoritmo de solver de produção;
- encoder/abstração privada final;
- orçamento exato de resolving em tempo de decisão.

Esses itens serão decididos por gates e benchmarks antes da run de meses.

## Estado atual — fundação

- repositório criado e inicializado;
- roadmap finito até `READY FOR TABLES` definido;
- arquitetura inicial documentada;
- contratos de canonicalização e action abstraction iniciados no Core;
- testes de invariância entram desde o primeiro commit;
- **treino longo ainda não autorizado**.

O roadmap canônico está em [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Regra de ouro

**Uma run de três meses sobre um modelo errado vale menos do que uma semana usada para provar que o modelo está certo.**

DeepCash só inicia o treino de produção depois que regras, invariâncias, encoder, action abstraction, solver e perfil físico do Ryzen estiverem congelados por evidência reproduzível.
