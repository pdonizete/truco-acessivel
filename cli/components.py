from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from core.rules import describe_card, is_manilha

if TYPE_CHECKING:
    from core.state import TrucoGame
    from core.deck import Card


def separator(title: str) -> str:
    return f"\n=== {title} ==="


def format_scoreboard(game: "TrucoGame") -> str:
    return (
        f"Placar da partida: voce {game.player_score} x {game.bot_score} computador.\n"
        f"Valor atual da mao: {game.hand_value} ponto(s).\n"
        f"Vira: {game.vira.display_name if game.vira else 'nao definida'}.\n"
        f"Manilha da vez: {game.manilha_rank if game.vira else 'nao definida'}."
    )


def format_points_status(game: "TrucoGame") -> str:
    return (
        f"Placar atual: voce {game.player_score} x {game.bot_score} computador.\n"
        f"Esta mao vale {game.hand_value} ponto(s)."
    )


def format_table(game: "TrucoGame") -> str:
    if not game.current_trick_cards:
        return "Mesa vazia nesta rodada."
    lines = ["Cartas na mesa nesta rodada:"]
    for player, card in game.current_trick_cards.items():
        owner = "Voce" if player == "jogador" else "Computador"
        lines.append(f"- {owner}: {card.display_name}")
    return "\n".join(lines)


def format_hand(cards: Iterable["Card"], game: "TrucoGame") -> str:
    lines = ["Suas cartas atuais:"]
    for index, card in enumerate(cards, start=1):
        manilha_text = " manilha." if is_manilha(card, game.vira) else ""
        lines.append(f"[{index}] {card.display_name}.{manilha_text} {describe_card(card, game.vira)}")
    return "\n".join(lines)


def format_history(history: list[str], limit: int = 8) -> str:
    if not history:
        return "Sem historico."
    lines = ["Historico recente:"]
    for entry in history[-limit:]:
        lines.append(f"- {entry}")
    return "\n".join(lines)


def format_options(options: list[tuple[str, str]]) -> str:
    lines = ["Opcoes disponiveis:"]
    for key, text in options:
        lines.append(f"[{key}] {text}")
    return "\n".join(lines)


def format_match_result(game: "TrucoGame") -> str:
    winner = "voce" if game.winner == "jogador" else "o computador"
    return (
        f"Partida encerrada. Vencedor: {winner}.\n"
        f"Placar final: voce {game.player_score} x {game.bot_score} computador."
    )


def format_stats(data: dict[str, object]) -> str:
    stats = data["estatisticas"]
    preferences = data["preferencias"]
    partidas = stats["partidas_concluidas"]
    win_rate = 0.0 if partidas == 0 else (stats["vitorias"] / partidas) * 100
    beep = "ativado" if preferences["beep_habilitado"] else "desativado"
    return (
        f"Vitorias: {stats['vitorias']}\n"
        f"Derrotas: {stats['derrotas']}\n"
        f"Partidas concluidas: {partidas}\n"
        f"Aproveitamento: {win_rate:.1f}%\n"
        f"Beep: {beep}\n"
        f"Dificuldade padrao: {preferences['dificuldade_padrao']}"
    )
