from __future__ import annotations

from core.rules import card_strength, compare_cards, is_manilha


def tutorial_intro() -> str:
    return (
        "Modo tutorial ativado.\n"
        "Objetivo: chegar a 12 pontos antes do computador.\n"
        "Cada mao vale 1 ponto e pode subir para 3, 6, 9 e 12 com os pedidos.\n"
        "A vira define a manilha: a carta seguinte na sequencia 4, 5, 6, 7, Q, J, K, A, 2, 3.\n"
        "Empates sao resolvidos pela ordem oficial das rodadas."
    )


def contextual_hint(game) -> str:
    if game.vira is None:
        return "O tutorial sera carregado assim que a primeira mao for distribuida."

    if game.pending_raise is not None and game.pending_raise.responder == "jogador":
        next_value = game.pending_raise.requested_value
        return (
            f"O computador pediu valor {next_value}. "
            "Aceitar mantem a disputa; correr entrega a mao; aumentar devolve a pressao."
        )

    hand = game.hands["jogador"]
    if not hand:
        return "Voce ja jogou todas as cartas desta mao."

    strongest = max(hand, key=lambda card: card_strength(card, game.vira))
    weakest = min(hand, key=lambda card: card_strength(card, game.vira))

    if "computador" in game.current_trick_cards:
        target = game.current_trick_cards["computador"]
        winning_cards = [
            card for card in hand if compare_cards(card, target, game.vira) > 0
        ]
        if winning_cards:
            recommended = min(
                winning_cards,
                key=lambda card: card_strength(card, game.vira),
            )
            return (
                f"Dica: o computador jogou {target.display_name}. "
                f"A menor carta sua que vence agora e {recommended.display_name}."
            )
        return (
            f"Dica: nenhuma carta sua vence {target.display_name}. "
            f"Normalmente vale guardar {strongest.display_name} e descartar {weakest.display_name}."
        )

    if is_manilha(strongest, game.vira):
        return (
            f"Dica: sua melhor carta e {strongest.display_name}, que e uma manilha. "
            "Considere pedir truco se o restante da mao tambem for bom."
        )
    return (
        f"Dica: sua carta mais forte agora e {strongest.display_name}. "
        f"Se quiser jogar com seguranca, preserve {strongest.display_name} e avalie começar com {weakest.display_name}."
    )


def explain_invalid_action(message: str) -> str:
    return (
        "Tutorial: a acao foi bloqueada. "
        f"Motivo identificado pelo jogo: {message}"
    )
