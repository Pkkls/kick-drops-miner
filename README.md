# Kick Drops Miner

Application desktop Windows qui fait avancer automatiquement le temps de visionnage
nécessaire pour débloquer les **drops Kick** (récompenses liées au visionnage d'un
stream) : scan des campagnes actives, sélection des chaînes à regarder, lecture
automatisée (AFK, son coupé) et affichage en direct de la progression.

Inspirée de [HyperBeats/KickDropsMiner](https://github.com/HyperBeats/KickDropsMiner).

![status](https://img.shields.io/badge/status-MVP-orange) ![platform](https://img.shields.io/badge/platform-Windows-blue) ![python](https://img.shields.io/badge/python-3.10%2B-green)

---

## Sommaire

- [Ce que fait l'app](#ce-que-fait-lapp)
- [Garanties de confidentialité](#garanties-de-confidentialité)
- [Installation](#installation)
- [Tutoriel pas à pas](#tutoriel-pas-à-pas)
- [Architecture technique](#architecture-technique)
- [Glossaire des termes techniques](#glossaire-des-termes-techniques)
- [Dépannage](#dépannage)
- [Avertissement](#avertissement)

---

## Ce que fait l'app

| Fonction | Détail |
|---|---|
| **Scan des campagnes** | Liste les campagnes de drops actives sur Kick (jeu, récompenses, chaînes éligibles). |
| **File de mining** | Tu ajoutes des chaînes Kick à une liste, avec un objectif de minutes chacune. |
| **Lecture automatisée** | Un Chrome dédié ouvre la chaîne, coupe le son, et la laisse jouer jusqu'à l'objectif. |
| **Statut live/offline** | Chaque chaîne de la liste affiche en temps réel si le streamer est en ligne. |
| **Glisser-déposer** | Réordonne la file en faisant glisser les lignes à la souris. |
| **Progression des drops** | Affiche l'avancement réel de chaque campagne (via ton compte connecté). |

## Garanties de confidentialité

- **Aucun serveur tiers, aucune télémétrie.** Le seul interlocuteur réseau est Kick.
- **Allowlist d'égress imposée par le code** (`core/egress.py`) : toute requête HTTP
  ou navigation Chrome passe par `assert_allowed()`, qui n'autorise que `*.kick.com`
  et lève une erreur (`EgressError`) sur tout le reste.
- **Login local** : tu te connectes dans une fenêtre Chrome dédiée, isolée de ton
  navigateur principal. Les cookies de session restent sur ton disque
  (`data/`, ignoré par git) et ne sont jamais transmis ailleurs qu'à Kick.
- **Code ouvert et auditable.**

Ce n'est pas un pare-feu OS, c'est une barrière applicative côté code. Pour une
preuve externe, lance l'app derrière un proxy (mitmproxy / Fiddler) : seul
`kick.com` doit apparaître dans le trafic.

## Installation

Prérequis : **Windows 10/11**, **Python 3.10+**, **Google Chrome** installé.

```powershell
git clone https://github.com/Pkkls/kick-drops-miner.git
cd kick-drops-miner
run.bat
```

`run.bat` crée l'environnement virtuel, installe les dépendances et lance l'app —
double-clique simplement sur le fichier pour les lancements suivants.

Installation manuelle (équivalente) :

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Tutoriel pas à pas

### 1. Se connecter à Kick

Clique sur **"Se connecter (cookies)"** dans la barre latérale.

- L'app tente d'abord d'importer automatiquement ta session si tu es déjà
  connecté dans Chrome ou Brave sur cette machine.
- Si l'import automatique échoue (cas le plus courant — voir
  [glossaire](#glossaire-des-termes-techniques) sur le chiffrement des cookies),
  une fenêtre Chrome dédiée s'ouvre : connecte-toi normalement à Kick dans cette
  fenêtre, puis ferme-la. Les cookies sont sauvegardés automatiquement.
- Une fois connecté, ton nom d'utilisateur Kick apparaît en vert sous le bouton.

### 2. Voir les campagnes de drops disponibles

Clique sur **"Campagnes Drops"**. La fenêtre liste toutes les campagnes actives :
jeu concerné, récompenses, et ta progression si tu es connecté.

### 3. Ajouter des chaînes à la file

Clique sur **"Ajouter un lien"**, colle une URL Kick (`https://kick.com/nom_du_streamer`),
choisis un objectif en minutes. Répète pour chaque chaîne à miner.

Double-clique sur une URL dans la liste pour l'ouvrir dans ton navigateur (vérifier
le contenu avant de lancer, par exemple).

### 4. Réordonner la file (optionnel)

Glisse une ligne de la liste vers le haut ou le bas avec la souris pour changer
l'ordre de passage.

### 5. Démarrer le mining

Clique sur **"Démarrer la file"**. L'app :
1. Vérifie que la première chaîne est bien en ligne (statut affiché dans la colonne).
2. Ouvre un Chrome headless dédié, charge la session, et lance le stream en muet.
3. Une fois l'objectif de minutes atteint, passe à la chaîne suivante.
4. Si une chaîne est hors ligne, elle est marquée et retentée plus tard.

Un seul stream tourne à la fois (limitation imposée par Kick côté serveur).

### 6. Arrêter

**"Stop sélection"** arrête le stream en cours sans toucher au reste de la file.

## Architecture technique

```
ui/app.py        → Interface (customtkinter), file de mining, affichage live/offline
core/api.py       → Appels HTTP directs à l'API Kick (campagnes, progression, statut live)
core/worker.py    → StreamWorker : pilote un Chrome headless pour regarder un stream
core/browser.py   → Création du driver Chrome (undetected-chromedriver) + gestion cookies
core/egress.py    → Allowlist réseau : bloque toute destination hors *.kick.com
core/config.py    → Persistance de la configuration locale (data/config.json)
utils/helpers.py  → Fonctions partagées (chemins, parsing d'URL, traductions)
```

**Pourquoi un vrai Chrome et pas de simples requêtes HTTP ?**
Kick est protégé par Cloudflare. Une requête HTTP nue (sans navigateur réel) est
bloquée. Pour les *lectures* d'API (campagnes, progression, statut live), l'app
contourne ça en envoyant les bons en-têtes et cookies de session directement en
HTTP — pas besoin de navigateur pour ça. Mais pour faire *progresser le watch-time*
d'un drop, Kick exige qu'un vrai lecteur vidéo tourne dans un navigateur connecté :
d'où le Chrome headless dédié au mining.

**Pourquoi exclure les cookies Cloudflare (`__cf_bm`, `_cfuvid`, `cf_clearance`)
lors de l'injection ?**
Ces cookies sont liés à l'empreinte du navigateur qui les a obtenus (IP, user-agent,
comportement). Les réinjecter dans un *autre* navigateur (le Chrome dédié de l'app)
casse la validation Cloudflare de ce nouveau navigateur. Seuls les cookies
d'authentification Kick (`session_token`, `kick_session`, etc.) sont réutilisés ;
Cloudflare émet ses propres cookies frais pour la nouvelle session Chrome.

## Glossaire des termes techniques

| Terme | Explication |
|---|---|
| **Selenium** | Bibliothèque qui permet de piloter un navigateur depuis du code (ouvrir une page, cliquer, lire le contenu) comme si un humain le faisait. |
| **undetected-chromedriver (UC)** | Variante de Selenium modifiée pour que les sites ne détectent pas qu'un robot pilote le navigateur (les sites bloquent souvent les navigateurs "automatisés" classiques). |
| **Headless** | Mode où Chrome tourne sans fenêtre visible à l'écran — utile pour le mining en arrière-plan. |
| **Cloudflare** | Service de protection anti-bot/anti-DDoS utilisé par Kick. Il analyse le comportement du navigateur et bloque les requêtes qui ressemblent à un script automatisé. |
| **Cookie** | Petit fichier texte qu'un site dépose dans le navigateur pour se souvenir de toi (session connectée, préférences). Le vol ou la réutilisation abusive d'un cookie de session permet d'usurper un compte — d'où l'attention portée à ne jamais les exposer. |
| **DPAPI** | "Data Protection API" de Windows : système de chiffrement utilisé par Chrome/Brave pour protéger les cookies stockés sur disque, lié au compte utilisateur Windows. |
| **session_token / kick_session** | Cookies qui identifient ta session Kick connectée. Ce sont les seuls réutilisés par l'app pour s'authentifier auprès de l'API. |
| **Allowlist d'égress** | Liste blanche des destinations réseau autorisées. Ici, seul `*.kick.com` ; toute tentative vers un autre domaine est bloquée par le code lui-même (`core/egress.py`). |
| **Watch-time** | Temps de visionnage cumulé d'un stream, calculé côté serveur Kick, qui déclenche le déblocage des drops une fois le seuil de la campagne atteint. |
| **AFK (Away From Keyboard)** | Ici : laisser un stream jouer sans interaction humaine pour accumuler du watch-time. |
| **Drag-and-drop** | Glisser-déposer : faire glisser un élément à la souris pour le déplacer (réordonner la file de mining). |

## Dépannage

- **"Se connecter" ouvre Chrome puis se ferme immédiatement** : vérifie que Chrome
  est installé et à jour. L'app détecte automatiquement la version installée.
- **Tous les streams affichent "OFFLINE" alors qu'ils sont en ligne** : ta session
  a probablement expiré — reconnecte-toi via "Se connecter (cookies)".
- **"Démarrer la file" ne fait rien** : vérifie le statut live affiché dans la
  colonne ; si tout est marqué OFFLINE, la file attend qu'une chaîne passe en
  ligne avant de démarrer.
- **Import automatique des cookies échoue** : c'est normal sur Chrome récent
  (chiffrement renforcé des cookies, "v20"). L'app bascule automatiquement sur la
  fenêtre de connexion manuelle.

## Avertissement

Le mining AFK automatisé de drops est contraire aux conditions d'utilisation de
Kick. Usage à tes propres risques (action possible sur le compte concerné).
