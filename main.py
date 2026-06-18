"""Point d'entree. Verifie la garantie d'egress puis lance l'UI."""
from core import egress
from ui.app import run

if __name__ == "__main__":
    egress.self_test()
    run()
