"""Acces a Kick via un Chrome local pilote (undetected-chromedriver).

Pourquoi un vrai navigateur : kick.com est derriere Cloudflare ; un simple
urllib renvoie 403. Le driver navigue uniquement sur kick.com (allowlist egress),
porte la session connectee (cookies du profil local) et execute les requetes
fetch() dans le contexte de la page.

Endpoints reels :
- scan des campagnes : https://web.kick.com/api/v1/drops/campaigns
- progression        : https://web.kick.com/api/v1/drops/progress
- etat d'une chaine  : https://kick.com/api/v2/channels/{slug}
- utilisateur connecte: https://kick.com/api/v2/user
"""
import json
import os
import time
from urllib.parse import urlparse

from .egress import assert_allowed

CAMPAIGNS_URL = "https://web.kick.com/api/v1/drops/campaigns"
PROGRESS_URL = "https://web.kick.com/api/v1/drops/progress"
CHANNEL_URL = "https://kick.com/api/v2/channels/{slug}"
USER_URL = "https://kick.com/api/v2/user"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME_PROFILE_DIR = os.path.join(_ROOT, "data", "chrome_profile")


def create_driver(headless: bool = False):
    """Cree un Chrome pilote, profil persistant local. Import paresseux pour que
    le parsing/les tests n'exigent pas Selenium installe."""
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--mute-audio")
    return uc.Chrome(options=options)


class KickClient:
    """Requetes JSON Kick executees dans le contexte de la page (cookies inclus)."""

    def __init__(self, driver):
        self.driver = driver

    def _ensure_on_kick(self, url: str = "") -> None:
        # ponytail: navigate to the correct domain so fetch() is same-origin (no CORS)
        want_web = urlparse(url).hostname == "web.kick.com"
        current_host = urlparse(self.driver.current_url or "").hostname or ""

        if want_web and current_host != "web.kick.com":
            self.driver.get(assert_allowed("https://web.kick.com"))
            self._wait_ready()
        elif not want_web and current_host not in ("kick.com", "www.kick.com"):
            self.driver.get(assert_allowed("https://kick.com"))
            self._wait_ready()

    def _wait_ready(self) -> None:
        for _ in range(20):
            try:
                if self.driver.execute_script("return document.readyState") == "complete":
                    return
            except Exception:
                pass
            time.sleep(0.5)

    def fetch_json(self, url: str):
        assert_allowed(url)
        self._ensure_on_kick(url)
        script = """
        const cb = arguments[arguments.length - 1];
        fetch(arguments[0], {credentials: 'include', headers: {'Accept': 'application/json'}})
          .then(r => r.text()).then(t => cb(t)).catch(e => cb('__ERR__' + e));
        """
        raw = self.driver.execute_async_script(script, url)
        if isinstance(raw, str) and raw.startswith("__ERR__"):
            raise RuntimeError(f"fetch kick echoue : {raw[7:]}")
        return json.loads(raw)

    def get_campaigns(self) -> list:
        return parse_campaigns(self.fetch_json(CAMPAIGNS_URL))

    def get_progress(self) -> list:
        resp = self.fetch_json(PROGRESS_URL)
        return resp.get("data", []) if isinstance(resp, dict) else []

    def is_live(self, slug: str) -> bool:
        try:
            resp = self.fetch_json(CHANNEL_URL.format(slug=slug))
        except Exception:
            return False
        return bool(isinstance(resp, dict) and resp.get("livestream"))


def parse_campaigns(response) -> list:
    """Transforme la reponse /drops/campaigns en modele interne."""
    campaigns = []
    data = response.get("data", []) if isinstance(response, dict) else []
    if not isinstance(data, list):
        return campaigns

    for campaign in data:
        if not isinstance(campaign, dict):
            continue
        category = campaign.get("category") or {}
        if not isinstance(category, dict):
            category = {}
        info = {
            "id": campaign.get("id"),
            "name": campaign.get("name", "Unknown Campaign"),
            "game": category.get("name", "Unknown Game"),
            "game_slug": category.get("slug", ""),
            "status": campaign.get("status", "unknown"),
            "starts_at": campaign.get("starts_at"),
            "ends_at": campaign.get("ends_at"),
            "rewards": campaign.get("rewards", []),
            "channels": [],
        }
        channels = campaign.get("channels", [])
        if isinstance(channels, list):
            for channel in channels:
                if isinstance(channel, dict):
                    slug = channel.get("slug")
                    if slug:
                        info["channels"].append({"slug": slug, "url": f"https://kick.com/{slug}"})
        if info["channels"] or campaign.get("status") == "active":
            campaigns.append(info)
    return campaigns
