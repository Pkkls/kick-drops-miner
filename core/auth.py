"""Login Kick - entierement local.

La session vit dans le profil Chrome persistant (data/chrome_profile), ecrit par
Chrome lui-meme sur le disque. L'app ne lit, ne copie, ni ne transmet jamais tes
identifiants : tu te connectes dans la fenetre Chrome, Kick pose ses cookies, le
profil les garde. Rien ne part vers un tiers.
"""
import time

from .egress import assert_allowed
from .kick import KickClient, USER_URL

LOGIN_URL = "https://kick.com/"


def is_logged_in(client: KickClient) -> bool:
    """Connecte si /api/v2/user (same-origin kick.com) retourne un id utilisateur."""
    try:
        resp = client.fetch_json(USER_URL)
        return bool(isinstance(resp, dict) and resp.get("id"))
    except Exception:
        return False


def wait_for_login(driver, timeout_sec: int = 300) -> bool:
    """Ouvre Kick et attend que l'utilisateur se connecte."""
    driver.get(assert_allowed(LOGIN_URL))
    deadline = time.time() + timeout_sec
    client = KickClient(driver)
    while time.time() < deadline:
        if is_logged_in(client):
            return True
        time.sleep(3)
    return False
