from __future__ import annotations

from pathlib import Path

from cli.interface import TerminalInterface
from core.persistence import ConfigStore


def main() -> None:
    root = Path(__file__).resolve().parent
    store = ConfigStore(root / "data" / "config.json")
    interface = TerminalInterface(store=store)
    interface.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExecucao interrompida pelo usuario. Se houver partida em andamento, ela foi preservada quando possivel.")
    except EOFError:
        print("\nEntrada encerrada. O jogo foi finalizado com seguranca.")
    except Exception as error:  # pragma: no cover - camada final de protecao
        print("O jogo encontrou um erro inesperado, mas foi encerrado com seguranca.")
        print(f"Detalhes amigaveis: {error}")
