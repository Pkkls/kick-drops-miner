"""Miner : fait avancer les timers de drops en jouant reellement le stream.

Kick compte le watch-time cote serveur tant qu'un vrai navigateur connecte joue
la chaine. Le miner ouvre la chaine selectionnee, garde le <video> en lecture
(muet par defaut), sonde la progression, et passe a la chaine suivante quand la
cible est atteinte ou que la chaine est hors ligne. Le claim est automatique cote
Kick : la progression passe au statut "claimed" une fois le seuil atteint.

Tourne dans un thread ; communique l'etat via un callback on_status(dict).
"""
import threading
import time

from .egress import assert_allowed
from .kick import KickClient

POLL_SEC = 30
ENSURE_PLAYING_JS = """
const v = document.querySelector('video');
if (v) {
  try { v.muted = arguments[0]; v.volume = arguments[0] ? 0 : 1; } catch (e) {}
  if (v.paused) { try { v.play(); } catch (e) {} }
  return true;
}
return false;
"""


class Miner:
    def __init__(self, driver, channels, target_minutes=120, mute=True, on_status=None):
        self.driver = driver
        self.client = KickClient(driver)
        self.channels = list(channels)        # slugs choisis au menu
        self.target_minutes = target_minutes
        self.mute = mute
        self.on_status = on_status or (lambda s: None)
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _emit(self, **kw):
        self.on_status(kw)

    def _run(self):
        for slug in self.channels:
            if self._stop.is_set():
                break
            self._mine_channel(slug)
        self._emit(state="done")

    def _mine_channel(self, slug: str):
        if not self.client.is_live(slug):
            self._emit(state="skip", channel=slug, reason="offline")
            return
        self.driver.get(assert_allowed(f"https://kick.com/{slug}"))
        time.sleep(5)

        started = time.time()
        target_sec = self.target_minutes * 60
        while not self._stop.is_set():
            playing = False
            try:
                playing = bool(self.driver.execute_script(ENSURE_PLAYING_JS, self.mute))
            except Exception:
                pass

            elapsed_min = int((time.time() - started) / 60)
            self._emit(state="mining", channel=slug, minutes=elapsed_min,
                       target=self.target_minutes, playing=playing)

            if time.time() - started >= target_sec:
                self._emit(state="target_reached", channel=slug)
                return
            if not self.client.is_live(slug):
                self._emit(state="skip", channel=slug, reason="went_offline")
                return

            self._stop.wait(POLL_SEC)
