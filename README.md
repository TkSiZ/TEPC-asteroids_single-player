# Asteroids Multiplayer

Este projeto é uma versão multiplayer local do clássico jogo Asteroids, desenvolvida em Python utilizando a biblioteca Pygame (pygame-ce). O jogo permite que dois jogadores compitam ou colaborem em um ambiente cheio de asteroides, OVNIs e agora, mecânicas especiais que tornam a experiência mais dinâmica e divertida.

## Autores

- **Joao Lucas Noronha de Castro**
- **Leonardo Melo Crispim**
- **Gustavo da Costa Frota**

## Novas Mecânicas

No último commit, foram adicionadas três mecânicas "engraçadas" que mudam a dinâmica do jogo:

1.  **Swap de Risco**:
    - Ao ativar o poder especial, inicia-se um contador de 1,5 segundos. Ao final desse tempo, as posições dos dois jogadores são trocadas.
    - É ideal para situações de perigo eminente ou para confundir o adversário.

2.  **Tiro da Confusão**:
    - Sempre que um jogador for atingido por um tiro disparado pelo outro jogador, seus controles de rotação serão invertidos por 3 segundos.
    - O efeito é indicado por uma cor diferenciada na nave atingida.

3.  **Bomba Gravitacional**:
    - Permite que o jogador gere um mini buraco negro em sua posição atual.
    - O buraco negro exerce uma força de atração sobre objetos próximos (como asteroides e outras naves), adicionando uma camada estratégica de controle de área.

### Controles das Mecânicas

- **P1 (Teclado)**: `RALT` para ativar o poder (Swap e Bomba Gravitacional).
- **P2 (Teclado)**: `N` para ativar o poder (Swap e Bomba Gravitacional).
- **Controle (Xbox)**: Botão `LB` para ativar o poder.

As mecânicas podem ser ativadas ou desativadas individualmente no menu de **PAUSE** (tecla `ESC` ou `P`) utilizando as teclas numéricas `1`, `2` e `3`.

## Como Executar

1. Certifique-se de ter o Python instalado.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o jogo:
   ```bash
   python main.py
   ```
