"""Acces a Kick via un Chrome local pilote (undetected-chromedriver).

Pourquoi un vrai navigateur : kick.com est derriere Cloudflare ; un simple
urllib renvoie 403. Le driver navigue uniquement sur kick.com (allowlist egress),
porte la session connectee (cookies du profil local) et execute les requetes
fetch() dans le contexte de la page.

Endpoints reels (verifies depuis HyperBeats/KickDropsMiner) :
- scan des campagnes : https://web.kick.com/api/v1/drops/campaigns
- progression        : https://web.kick.com/api/v1/drops/progress
- etat d'une chaine  : https://kick.com/api/v2/channels/{slug}
"""
import json

from .egress import assert_allowed

CAMPAIGNS_URL = "https://web.kick.com/api/v1/drops/campaigns"
PROGRESS_URL = "https://web.kick.com/api/v1/drops/progress"
CHANNEL_URL = "https://kick.com/api/v2/channels/{slug}"

CHROME_PROFILE_DIR = "data/chrome_profile"  # profil reutilisable, local


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

    def _ensure_on_kick(self) -> None:
        url = (self.driver.current_url or "")
        if "kick.com" not in url:
            self.driver.get(assert_allowed("https://kick.com"))

    def fetch_json(self, url: str):
        assert_allowed(url)
        self._ensure_on_kick()
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
    """Transforme la reponse /drops/campaigns en modele interne.

    Portage fidele de _campaigns_from_response (KickDropsMiner) : on garde les
    campagnes actives ou ayant des chaines participantes.
    """
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
