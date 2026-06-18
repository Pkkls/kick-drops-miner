"""Login Kick — entierement local.

La session vit dans le profil Chrome persistant (data/chrome_profile), ecrit par
Chrome lui-meme sur le disque. L'app ne lit, ne copie, ni ne transmet jamais tes
identifiants : tu te connectes dans la fenetre Chrome, Kick pose ses cookies, le
profil les garde. Rien ne part vers un tiers.
"""
import time

from .egress import assert_allowed
from .kick import KickClient

LOGIN_URL = "https://kick.com/"


def is_logged_in(client: KickClient) -> bool:
    """Connecte si l'endpoint de progression (authentifie) repond une liste."""
    try:
        client.get_progress()
        return True
    except Exception:
        return False


def wait_for_login(driver, timeout_sec: int = 300) -> bool:
    """Ouvre Kick et attend que l'utilisateur se connecte (cookie de session)."""
    driver.get(assert_allowed(LOGIN_URL))
    deadline = time.time() + timeout_sec
    client = KickClient(driver)
    while time.time() < deadline:
        if _has_session_cookie(driver) and is_logged_in(client):
            return True
        time.sleep(2)
    return False


def _has_session_cookie(driver) -> bool:
    try:
        return any(c.get("name") == "session_token" for c in driver.get_cookies())
    except Exception:
        return False
