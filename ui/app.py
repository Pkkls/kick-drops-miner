"""Interface CustomTkinter : login, scan des drops, selection au menu, mining."""
import threading

import customtkinter as ctk

from core import auth, store
from core.kick import KickClient, create_driver
from core.miner import Miner


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kick Drops Miner (local)")
        self.geometry("640x720")
        ctk.set_appearance_mode("dark")

        self.config_data = store.load_config()
        self.driver = None
        self.client = None
        self.miner = None
        self.campaigns = []
        self.channel_vars = {}   # slug -> BooleanVar (selection au menu)

        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(top, text="Kick Drops Miner", font=("", 18, "bold")).pack(side="left")
        self.status_dot = ctk.CTkLabel(top, text="● hors ligne", text_color="#ef4444")
        self.status_dot.pack(side="right")

        bar = ctk.CTkFrame(self)
        bar.pack(fill="x", padx=12)
        ctk.CTkButton(bar, text="Se connecter (Chrome)", command=self._login).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Scanner les drops", command=self._scan).pack(side="left", padx=4)

        opts = ctk.CTkFrame(self)
        opts.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(opts, text="Objectif (min)/chaine :").pack(side="left", padx=4)
        self.target_entry = ctk.CTkEntry(opts, width=70)
        self.target_entry.insert(0, str(self.config_data.get("target_minutes", 120)))
        self.target_entry.pack(side="left")
        self.mute_var = ctk.BooleanVar(value=self.config_data.get("mute", True))
        ctk.CTkCheckBox(opts, text="Muet", variable=self.mute_var).pack(side="left", padx=10)

        ctk.CTkLabel(self, text="Drops disponibles (coche les chaines a miner) :").pack(
            anchor="w", padx=14)
        self.list_frame = ctk.CTkScrollableFrame(self, height=360)
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=6)

        run = ctk.CTkFrame(self)
        run.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(run, text="Demarrer le mining", fg_color="#16a34a",
                      command=self._start).pack(side="left", padx=4)
        ctk.CTkButton(run, text="Arreter", fg_color="#b91c1c",
                      command=self._stop).pack(side="left", padx=4)

        self.log_box = ctk.CTkTextbox(self, height=120)
        self.log_box.pack(fill="x", padx=12, pady=(0, 12))

    def _log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def _set_online(self, ok):
        self.status_dot.configure(text="● connecte" if ok else "● hors ligne",
                                  text_color="#22c55e" if ok else "#ef4444")

    # ── Driver / login ──────────────────────────────────────────────────────────
    def _ensure_driver(self):
        if self.driver is None:
            self._log("Lancement de Chrome (profil local)...")
            self.driver = create_driver(headless=self.config_data.get("headless", False))
            self.client = KickClient(self.driver)

    def _login(self):
        def work():
            try:
                self._ensure_driver()
                self._log("Connecte-toi dans la fenetre Chrome puis attends...")
                ok = auth.wait_for_login(self.driver)
                self._set_online(ok)
                self._log("Connecte." if ok else "Login non detecte (timeout).")
            except Exception as e:
                self._log(f"Erreur login : {e}")
        threading.Thread(target=work, daemon=True).start()

    # ── Scan ──────────────────────────────────────────────────────────────────
    def _scan(self):
        def work():
            try:
                self._ensure_driver()
                self._log("Scan des campagnes de drops...")
                self.campaigns = self.client.get_campaigns()
                self._set_online(True)
                self.after(0, self._render_campaigns)
                self._log(f"{len(self.campaigns)} campagne(s) trouvee(s).")
            except Exception as e:
                self._log(f"Erreur scan : {e}")
        threading.Thread(target=work, daemon=True).start()

    def _render_campaigns(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.channel_vars.clear()
        saved = set(self.config_data.get("selected_channels", []))

        for c in self.campaigns:
            head = f"{c['name']}  —  {c['game']}  [{c['status']}]"
            ctk.CTkLabel(self.list_frame, text=head, font=("", 13, "bold")).pack(
                anchor="w", pady=(8, 0))
            if not c["channels"]:
                ctk.CTkLabel(self.list_frame, text="  (aucune chaine en ligne)",
                             text_color="#9ca3af").pack(anchor="w")
            for ch in c["channels"]:
                slug = ch["slug"]
                var = ctk.BooleanVar(value=slug in saved)
                self.channel_vars[slug] = var
                ctk.CTkCheckBox(self.list_frame, text=slug, variable=var).pack(
                    anchor="w", padx=18)

    def _selected_slugs(self):
        return [slug for slug, var in self.channel_vars.items() if var.get()]

    # ── Mining ────────────────────────────────────────────────────────────────
    def _start(self):
        slugs = self._selected_slugs()
        if not slugs:
            self._log("Aucune chaine selectionnee.")
            return
        try:
            target = int(self.target_entry.get())
        except ValueError:
            target = 120
        self.config_data.update(target_minutes=target, mute=self.mute_var.get(),
                                selected_channels=slugs)
        store.save_config(self.config_data)

        self._ensure_driver()
        self.miner = Miner(self.driver, slugs, target_minutes=target,
                           mute=self.mute_var.get(), on_status=self._on_status)
        self.miner.start()
        self._log(f"Mining demarre sur : {', '.join(slugs)}")

    def _stop(self):
        if self.miner:
            self.miner.stop()
            self._log("Arret demande.")

    def _on_status(self, s):
        state = s.get("state")
        if state == "mining":
            txt = f"[{s['channel']}] {s['minutes']}/{s['target']} min  (video {'OK' if s['playing'] else '...'})"
        elif state == "skip":
            txt = f"[{s['channel']}] saute ({s.get('reason')})"
        elif state == "target_reached":
            txt = f"[{s['channel']}] objectif atteint."
        elif state == "done":
            txt = "File terminee."
        else:
            txt = str(s)
        self.after(0, lambda: self._log(txt))


def run():
    App().mainloop()
