# Kick Drops Miner (local)

App desktop locale qui fait avancer les timers de **drops Kick** en AFK : scan des
drops disponibles, selection des chaines au menu, mining (lecture reelle du stream,
muet) et claim automatique (cote Kick).

Inspiree de [HyperBeats/KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner).
Statut : **MVP**. Rien n'est publie.

## Garantie : rien ne sort de ton PC

- **Aucun serveur tiers, aucune telemetrie.** Le seul interlocuteur reseau est Kick.
- **Allowlist d'egress imposee par le code** : toute URL passe par `core/egress.py`,
  qui n'autorise que `*.kick.com` et leve une erreur sur tout le reste. Verifiable
  au demarrage (`egress.self_test()`).
- **Login local** : tu te connectes dans la fenetre Chrome ; Kick pose ses cookies
  dans le profil Chrome local (`data/chrome_profile/`). L'app ne lit, copie, ni
  transmet jamais tes identifiants ailleurs que vers Kick.
- **Tout reste sur disque** : profil, config (`data/`), tous git-ignores.
- **Code ouvert et auditable.**

Ce n'est pas un pare-feu OS, c'est une barriere applicative. Pour une **preuve
externe**, lance derriere un proxy (mitmproxy / Fiddler) : seul `kick.com` apparait.

## Pourquoi un vrai Chrome (et un login)

Kick est derriere Cloudflare : un appel HTTP nu renvoie 403. L'app pilote donc un
Chrome local (undetected-chromedriver) qui porte ta session connectee. Le login est
**requis** car les drops sont lies a ton compte ; le watch-time se compte cote Kick
tant qu'un navigateur connecte joue la chaine.

## Installation

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Prerequis : Windows 10/11, Python 3.10+, Google Chrome installe.

## Utilisation

1. **Se connecter (Chrome)** : connecte-toi a Kick dans la fenetre.
2. **Scanner les drops** : liste les campagnes actives et leurs chaines en ligne.
3. **Selection au menu** : coche les chaines a miner.
4. **Demarrer** : le miner ouvre chaque chaine, garde la video active jusqu'a
   l'objectif (minutes/chaine), puis passe a la suivante.

## Endpoints Kick utilises (lecture seule, authentifiee)

- `https://web.kick.com/api/v1/drops/campaigns` — scan des campagnes
- `https://web.kick.com/api/v1/drops/progress` — progression / statut `claimed`
- `https://kick.com/api/v2/channels/{slug}` — etat live d'une chaine

## Avertissement

Le mining AFK automatise de drops est contraire aux conditions d'utilisation de
Kick. Usage a tes risques (action possible sur le compte).
