# Truco Acessivel

Truco Acessivel e um jogo de Truco Brasileiro para terminal, com foco em comandos simples, saida textual clara e fluxo jogavel inteiramente pelo teclado.

O projeto implementa uma partida contra o computador, com regras de mao, vira, manilhas, pedidos de truco, aumento para seis/nove/doze, persistencia de partida em andamento, estatisticas locais e modo tutorial.

## Recursos

- Cliente de jogo em terminal, sem interface grafica obrigatoria.
- Partidas contra bot com tres dificuldades: iniciante, intermediario e expert.
- Modo tutorial com dicas contextuais durante a partida.
- Continuacao de partida salva automaticamente.
- Estatisticas locais de vitorias, derrotas e partidas concluidas.
- Preferencias persistidas, incluindo dificuldade padrao e aviso sonoro opcional.
- Regras testadas com `unittest`.

## Requisitos

- Python 3.10 ou superior.
- Terminal com suporte a entrada interativa.

O projeto usa apenas a biblioteca padrao do Python. Nao ha dependencias externas obrigatorias.

## Como Executar o Cliente

Clone o repositorio e entre na pasta do projeto:

```bash
git clone https://github.com/pdonizete/truco-acessivel.git
cd truco-acessivel
```

Inicie o cliente do jogo:

```bash
python3 main.py
```

No menu principal, escolha uma das opcoes:

```text
[1] Nova partida
[2] Continuar partida salva
[3] Nova partida com tutorial
[4] Estatisticas e configuracoes
[5] Sair
```

Durante a partida, o cliente mostra o placar, a vira, a manilha, as cartas na mesa, suas cartas e o historico recente. As acoes sao escolhidas por teclas simples:

- Digite o numero da carta para jogar.
- Digite `T` para pedir truco ou aumentar o valor da mao quando a acao estiver disponivel.
- Digite `P` para consultar os pontos atuais sem passar a vez.
- Digite `F` para correr da mao.
- Ao responder um pedido do computador, escolha aceitar, aumentar ou correr pelas opcoes numeradas exibidas no terminal.

## Como Jogar

O objetivo e chegar a 12 pontos antes do computador.

Cada mao comeca valendo 1 ponto. O valor pode subir para 3, 6, 9 e 12 por meio dos pedidos de truco e aumentos. Se um jogador corre de um pedido, o adversario recebe os pontos correspondentes ao valor anterior do pedido.

A vira define a manilha da mao. A manilha e a carta seguinte na sequencia:

```text
4, 5, 6, 7, Q, J, K, A, 2, 3
```

Entre manilhas, a ordem dos naipes e:

```text
ouros < espadas < copas < paus
```

## Modo Tutorial

Use a opcao `Nova partida com tutorial` para receber dicas contextuais. O tutorial explica o estado da mao, recomenda leituras basicas de cartas e ajuda a entender por que uma acao invalida foi bloqueada.

Esse modo e recomendado para quem esta conhecendo as regras ou quer validar o fluxo do cliente com mais orientacao textual.

## Configuracoes e Estado Local

O jogo cria e atualiza automaticamente o arquivo `data/config.json` durante o uso local. Esse arquivo guarda estatisticas, preferencias e uma partida salva.

Por conter dados locais do jogador, `data/config.json` nao deve ser versionado. Em uma instalacao nova, ele sera recriado automaticamente com valores padrao quando o cliente for executado.

## Testes

Execute a suite de testes com:

```bash
python3 -m unittest discover -s tests
```

Os testes cobrem regras centrais do Truco, decisoes do bot e pontos importantes da interface de terminal.

## Estrutura do Projeto

```text
.
├── ai/              # Decisoes do bot e niveis de dificuldade
├── cli/             # Cliente de terminal, componentes textuais e tutorial
├── core/            # Baralho, regras, estado de jogo e persistencia
├── data/            # Estado local criado em tempo de execucao
├── tests/           # Testes unitarios
└── main.py          # Ponto de entrada do cliente
```

## Para Desenvolvedores

Fluxo recomendado:

```bash
python3 -m unittest discover -s tests
python3 main.py
```

Antes de abrir um pull request, verifique:

- O cliente continua executando pelo comando `python3 main.py`.
- As regras alteradas possuem testes.
- Arquivos de cache, estatisticas locais e partidas salvas nao foram adicionados ao commit.
- Textos da interface continuam claros para uso por teclado e leitores de tela.

## Roadmap

- Suporte a mais variantes regionais de Truco.
- Melhor cobertura de testes para fluxos completos de partida.
- Empacotamento para instalacao via `pipx` ou comando dedicado.
- Opcoes adicionais de acessibilidade textual.

## Licenca

Este projeto ainda nao define uma licenca publica. Antes de reutilizar, distribuir ou publicar alteracoes, abra uma issue para alinhamento com os mantenedores.
