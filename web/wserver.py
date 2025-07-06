from uvloop import install

install()
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, WARNING
from asyncio import sleep
from sabnzbdapi import SabnzbdClient
from aioaria2 import Aria2HttpClient
from aioqbt.client import create_client
from aiohttp.client_exceptions import ClientError
from aioqbt.exc import AQError

from web.nodes import extract_file_ids, make_tree

getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp").setLevel(WARNING)

aria2 = None
qbittorrent = None
sabnzbd_client = SabnzbdClient(
    host="http://localhost",
    api_key="mltb",
    port="8070",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global aria2, qbittorrent
    aria2 = Aria2HttpClient("http://localhost:6800/jsonrpc")
    qbittorrent = await create_client("http://localhost:8090/api/v2/")
    yield
    await aria2.close()
    await qbittorrent.close()


app = FastAPI(lifespan=lifespan)


templates = Jinja2Templates(directory="web/templates/")

basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)

LOGGER = getLogger(__name__)


async def re_verify(paused, resumed, hash_id):
    k = 0
    while True:
        res = await qbittorrent.torrents.files(hash_id)
        verify = True
        for i in res:
            if i.index in paused and i.priority != 0:
                verify = False
                break
            if i.index in resumed and i.priority == 0:
                verify = False
                break
        if verify:
            break
        LOGGER.info("Échec de la revérification ! Correction en cours...")
        await sleep(0.5)
        if paused:
            try:
                await qbittorrent.torrents.file_prio(
                    hash=hash_id, id=paused, priority=0
                )
            except (ClientError, TimeoutError, Exception, AQError) as e:
                LOGGER.error(f"{e} Erreur lors de la revérification (paused)!")
        if resumed:
            try:
                await qbittorrent.torrents.file_prio(
                    hash=hash_id, id=resumed, priority=1
                )
            except (ClientError, TimeoutError, Exception, AQError) as e:
                LOGGER.error(f"{e} Erreur lors de la revérification (resumed)!")
        k += 1
        if k > 5:
            return False
    LOGGER.info(f"Vérifié ! Hachage : {hash_id}")
    return True


@app.get("/app/files", response_class=HTMLResponse)
async def files(request: Request):
    return templates.TemplateResponse("page.html", {"request": request})


@app.api_route(
    "/app/files/torrent", methods=["GET", "POST"], response_class=HTMLResponse
)
async def handle_torrent(request: Request):
    params = request.query_params

    if not (gid := params.get("gid")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "GID manquant",
                "message": "GID non spécifié",
            }
        )

    if not (pin := params.get("pin")):
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "PIN manquant",
                "message": "PIN non spécifié",
            }
        )

    code = "".join([nbr for nbr in gid if nbr.isdigit()][:4])
    if code != pin:
        return JSONResponse(
            {
                "files": [],
                "engine": "",
                "error": "PIN invalide",
                "message": "Le PIN que vous avez entré est incorrect",
            }
        )

    if request.method == "POST":
        if not (mode := params.get("mode")):
            return JSONResponse(
                {
                    "files": [],
                    "engine": "",
                    "error": "Mode non spécifié",
                    "message": "Mode non spécifié",
                }
            )
        data = await request.json()
        if mode == "rename":
            if len(gid) > 20:
                await handle_rename(gid, data)
                content = {
                    "files": [],
                    "engine": "",
                    "error": "",
                    "message": "Renommage réussi.",
                }
            else:
                content = {
                    "files": [],
                    "engine": "",
                    "error": "Échec du renommage.",
                    "message": "Impossible de renommer le fichier torrent aria2c",
                }
        else:
            selected_files, unselected_files = extract_file_ids(data)
            if gid.startswith("SABnzbd_nzo"):
                await set_sabnzbd(gid, unselected_files)
            elif len(gid) > 20:
                await set_qbittorrent(gid, selected_files, unselected_files)
            else:
                selected_files = ",".join(selected_files)
                await set_aria2(gid, selected_files)
            content = {
                "files": [],
                "engine": "",
                "error": "",
                "message": "Votre sélection a été soumise avec succès.",
            }
    else:
        try:
            if gid.startswith("SABnzbd_nzo"):
                res = await sabnzbd_client.get_files(gid)
                content = make_tree(res, "sabnzbd")
            elif len(gid) > 20:
                res = await qbittorrent.torrents.files(gid)
                content = make_tree(res, "qbittorrent")
            else:
                res = await aria2.getFiles(gid)
                op = await aria2.getOption(gid)
                fpath = f"{op['dir']}/"
                content = make_tree(res, "aria2", fpath)
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(str(e))
            content = {
                "files": [],
                "engine": "",
                "error": "Erreur lors de la récupération des fichiers",
                "message": str(e),
            }
    return JSONResponse(content)


async def handle_rename(gid, data):
    try:
        _type = data["type"]
        del data["type"]
        if _type == "file":
            await qbittorrent.torrents.rename_file(hash=gid, **data)
        else:
            await qbittorrent.torrents.rename_folder(hash=gid, **data)
    except (ClientError, TimeoutError, Exception, AQError) as e:
        LOGGER.error(f"{e} Erreur lors du renommage")


async def set_sabnzbd(gid, unselected_files):
    await sabnzbd_client.remove_file(gid, unselected_files)
    LOGGER.info(f"Vérifié ! nzo_id: {gid}")


async def set_qbittorrent(gid, selected_files, unselected_files):
    if unselected_files:
        try:
            await qbittorrent.torrents.file_prio(
                hash=gid, id=unselected_files, priority=0
            )
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(f"{e} Erreur (paused)")
    if selected_files:
        try:
            await qbittorrent.torrents.file_prio(
                hash=gid, id=selected_files, priority=1
            )
        except (ClientError, TimeoutError, Exception, AQError) as e:
            LOGGER.error(f"{e} Erreur (resumed)")
    await sleep(0.5)
    if not await re_verify(unselected_files, selected_files, gid):
        LOGGER.error(f"Échec de la vérification ! Hachage : {gid}")


async def set_aria2(gid, selected_files):
    res = await aria2.changeOption(gid, {"select-file": selected_files})
    if res == "OK":
        LOGGER.info(f"Vérifié ! Gid: {gid}")
    else:
        LOGGER.info(f"Échec de la vérification ! Rapport requis ! Gid: {gid}")


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mirror-Leech Bot - Roadmap 2026</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #4361ee;
                --secondary: #3f37c9;
                --accent: #4895ef;
                --dark: #0f172a;
                --light: #f8f9fa;
                --card-bg: rgba(30, 41, 59, 0.7);
                --success: #10b981;
                --warning: #f59e0b;
                --info: #3b82f6;
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f172a, #1e293b);
                color: #e2e8f0;
                min-height: 100vh;
                padding: 20px;
                line-height: 1.6;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }

            header {
                text-align: center;
                padding: 40px 0;
                margin-bottom: 30px;
                animation: fadeIn 1s ease;
            }

            .logo {
                display: inline-flex;
                width: 100px;
                height: 100px;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                border-radius: 20px;
                align-items: center;
                justify-content: center;
                margin-bottom: 25px;
                box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3);
            }

            .logo i {
                font-size: 3.5rem;
                color: white;
            }

            h1 {
                font-size: 3rem;
                margin-bottom: 15px;
                background: linear-gradient(90deg, #60a5fa, #3b82f6);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                font-weight: 700;
            }

            .tagline {
                font-size: 1.3rem;
                max-width: 800px;
                margin: 0 auto 30px;
                color: #94a3b8;
                font-weight: 400;
            }

            .stats-container {
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 20px;
                margin: 40px 0;
            }

            .stat-card {
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                padding: 25px;
                text-align: center;
                min-width: 200px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: transform 0.3s ease;
            }

            .stat-card:hover {
                transform: translateY(-5px);
            }

            .stat-value {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 10px;
                background: linear-gradient(90deg, var(--primary), var(--accent));
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
            }

            .stat-label {
                font-size: 1rem;
                color: #cbd5e1;
                font-weight: 500;
            }

            .roadmap-section {
                position: relative;
                padding: 50px 0;
                margin: 60px 0;
            }

            .section-title {
                text-align: center;
                font-size: 2.5rem;
                margin-bottom: 60px;
                position: relative;
                display: inline-block;
                left: 50%;
                transform: translateX(-50%);
            }

            .section-title span {
                background: linear-gradient(90deg, var(--primary), var(--accent));
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
                position: relative;
            }

            .section-title::after {
                content: '';
                position: absolute;
                width: 80%;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--accent));
                bottom: -15px;
                left: 10%;
                border-radius: 2px;
            }

            /* Timeline */
            .timeline {
                position: relative;
                max-width: 1000px;
                margin: 0 auto;
            }

            /* Ligne de la timeline */
            .timeline::after {
                content: '';
                position: absolute;
                width: 4px;
                background: linear-gradient(to bottom, var(--primary), var(--accent));
                top: 0;
                bottom: 0;
                left: 50%;
                margin-left: -2px;
                border-radius: 10px;
            }

            /* Conteneur des étapes */
            .timeline-container {
                padding: 10px 40px;
                position: relative;
                width: 50%;
                opacity: 0;
                transform: translateY(30px);
                transition: all 0.8s ease;
            }

            .timeline-container.show {
                opacity: 1;
                transform: translateY(0);
            }

            /* Placement alterné des étapes */
            .left {
                left: 0;
            }

            .right {
                left: 50%;
            }

            /* Style des cartes */
            .timeline-card {
                padding: 30px;
                background: var(--card-bg);
                backdrop-filter: blur(10px);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                position: relative;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }

            .timeline-card::after {
                content: '';
                position: absolute;
                border-width: 10px;
                border-style: solid;
                top: 30px;
            }

            /* Flèches pour les cartes à gauche */
            .left::after {
                right: -15px;
                border-color: transparent transparent transparent var(--card-bg);
            }

            /* Flèches pour les cartes à droite */
            .right::after {
                left: -15px;
                border-color: transparent var(--card-bg) transparent transparent;
            }

            /* Points sur la ligne */
            .timeline-container::before {
                content: '';
                position: absolute;
                width: 25px;
                height: 25px;
                background: linear-gradient(135deg, var(--primary), var(--accent));
                border: 4px solid var(--dark);
                border-radius: 50%;
                top: 30px;
                z-index: 1;
            }

            .left::before {
                right: -12px;
            }

            .right::before {
                left: -12px;
            }

            /* Dates */
            .timeline-date {
                font-weight: 600;
                color: var(--accent);
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                font-size: 1.1rem;
            }

            .timeline-date i {
                margin-right: 10px;
                font-size: 1.2rem;
            }

            .timeline-card h3 {
                font-size: 1.5rem;
                margin-bottom: 15px;
                color: #fff;
                display: flex;
                align-items: center;
            }

            .timeline-card h3 i {
                margin-right: 10px;
                width: 35px;
                height: 35px;
                background: rgba(67, 97, 238, 0.2);
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }

            .timeline-card ul {
                padding-left: 20px;
                color: #cbd5e1;
            }

            .timeline-card li {
                margin-bottom: 12px;
                position: relative;
                padding-left: 10px;
            }

            .timeline-card li::before {
                content: '•';
                color: var(--accent);
                font-weight: bold;
                display: inline-block;
                width: 1em;
                margin-left: -1em;
            }

            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                margin-top: 15px;
            }

            .status-planned {
                background: rgba(59, 130, 246, 0.2);
                color: var(--info);
            }

            .status-in-progress {
                background: rgba(245, 158, 11, 0.2);
                color: var(--warning);
            }

            .status-completed {
                background: rgba(16, 185, 129, 0.2);
                color: var(--success);
            }

            .cta-section {
                text-align: center;
                padding: 60px 0 40px;
            }

            .cta-button {
                display: inline-flex;
                align-items: center;
                padding: 16px 40px;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                color: white;
                text-decoration: none;
                font-weight: 600;
                font-size: 1.1rem;
                border-radius: 12px;
                margin: 10px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
                border: none;
                cursor: pointer;
            }

            .cta-button i {
                margin-right: 10px;
                font-size: 1.2rem;
            }

            .cta-button:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(37, 99, 235, 0.6);
                background: linear-gradient(90deg, var(--secondary), var(--primary));
            }

            .author {
                margin-top: 30px;
                padding-top: 30px;
                text-align: center;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                color: #94a3b8;
                font-size: 1.1rem;
            }

            .author a {
                color: #60a5fa;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s;
            }

            .author a:hover {
                color: #93c5fd;
                text-decoration: underline;
            }

            /* Animations */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }

            @media (max-width: 768px) {
                .timeline::after {
                    left: 31px;
                }

                .timeline-container {
                    width: 100%;
                    padding-left: 70px;
                    padding-right: 25px;
                }

                .right {
                    left: 0;
                }

                .left::after, .right::after {
                    left: 15px;
                    border-color: transparent var(--card-bg) transparent transparent;
                }

                .left::before, .right::before {
                    left: 18px;
                }

                h1 { font-size: 2.2rem; }
                .tagline { font-size: 1.1rem; }
                .section-title { font-size: 2rem; }
                .stat-card { min-width: 140px; padding: 20px 15px; }
                .stat-value { font-size: 2rem; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="logo">
                    <i class="fas fa-robot"></i>
                </div>
                <h1>Mirror-Leech Bot</h1>
                <p class="tagline">
                    Solution tout-en-un pour télécharger, convertir et gérer vos fichiers
                </p>

                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-value">20+</div>
                        <div class="stat-label">Plateformes supportées</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">100K+</div>
                        <div class="stat-label">Utilisateurs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">24/7</div>
                        <div class="stat-label">Disponibilité</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">2026</div>
                        <div class="stat-label">Roadmap ambitieuse</div>
                    </div>
                </div>
            </header>

            <section class="roadmap-section">
                <h2 class="section-title">📅 <span>Roadmap 2026</span></h2>

                <div class="timeline">
                    <!-- Étape 1 -->
                    <div class="timeline-container left">
                        <div class="timeline-card">
                            <div class="timeline-date">
                                <i class="fas fa-calendar-alt"></i> Q1 2026
                            </div>
                            <h3><i class="fas fa-cloud"></i> Intégration Cloud Avancée</h3>
                            <ul>
                                <li>Support OneDrive et Dropbox</li>
                                <li>Transfert direct entre clouds</li>
                                <li>Gestion des comptes multiples</li>
                                <li>Synchronisation automatique</li>
                            </ul>
                            <div class="status-badge status-in-progress">En développement</div>
                        </div>
                    </div>

                    <!-- Étape 2 -->
                    <div class="timeline-container right">
                        <div class="timeline-card">
                            <div class="timeline-date">
                                <i class="fas fa-calendar-alt"></i> Q2 2026
                            </div>
                            <h3><i class="fas fa-brain"></i> Intelligence Artificielle</h3>
                            <ul>
                                <li>Reconnaissance vocale pour commandes</li>
                                <li>Classification automatique des fichiers</li>
                                <li>Recommandations intelligentes</li>
                                <li>Détection de contenu inapproprié</li>
                            </ul>
                            <div class="status-badge status-planned">Planifié</div>
                        </div>
                    </div>

                    <!-- Étape 3 -->
                    <div class="timeline-container left">
                        <div class="timeline-card">
                            <div class="timeline-date">
                                <i class="fas fa-calendar-alt"></i> Q3 2026
                            </div>
                            <h3><i class="fas fa-expand"></i> Nouvelles Plateformes</h3>
                            <ul>
                                <li>Support Twitch et Dailymotion</li>
                                <li>Téléchargement depuis Netflix (via lien)</li>
                                <li>Intégration Pinterest</li>
                                <li>Support des podcasts Spotify</li>
                            </ul>
                            <div class="status-badge status-planned">Planifié</div>
                        </div>
                    </div>

                    <!-- Étape 4 -->
                    <div class="timeline-container right">
                        <div class="timeline-card">
                            <div class="timeline-date">
                                <i class="fas fa-calendar-alt"></i> Q4 2026
                            </div>
                            <h3><i class="fas fa-cogs"></i> Écosystème Étendu</h3>
                            <ul>
                                <li>Application mobile dédiée</li>
                                <li>Plugin navigateur</li>
                                <li>API publique v2.0</li>
                                <li>Marketplace d'extensions</li>
                            </ul>
                            <div class="status-badge status-planned">Planifié</div>
                        </div>
                    </div>

                    <!-- Étape 5 (complétée) -->
                    <div class="timeline-container left">
                        <div class="timeline-card">
                            <div class="timeline-date">
                                <i class="fas fa-calendar-alt"></i> Q4 2025
                            </div>
                            <h3><i class="fas fa-bolt"></i> Optimisation Performances</h3>
                            <ul>
                                <li>Vitesse de téléchargement ×2</li>
                                <li>Nouveau système de file d'attente</li>
                                <li>Compression améliorée (50% gain d'espace)</li>
                                <li>Support multi-thread</li>
                            </ul>
                            <div class="status-badge status-completed">Complété</div>
                        </div>
                    </div>
                </div>
            </section>

            <div class="cta-section">
                <a href="https://t.me/hyoshcoder" class="cta-button">
                    <i class="fab fa-telegram"></i> Rejoindre sur Telegram
                </a>
                <a href="https://t.me/hyoshcoder" class="cta-button">
                    <i class="fab fa-github"></i> Voir sur GitHub
                </a>
            </div>

            <div class="author">
                Développé avec <i class="fas fa-heart" style="color: #ef4444;"></i> par
                <a href="https://t.me/hyoshcoder">Anas</a>
            </div>
        </div>

        <script>
            // Animation de la timeline au défilement
            document.addEventListener('DOMContentLoaded', function() {
                const timelineContainers = document.querySelectorAll('.timeline-container');

                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('show');
                        }
                    });
                }, { threshold: 0.15 });

                timelineContainers.forEach(container => {
                    observer.observe(container);
                });

                // Animation des cartes de statistiques
                const statCards = document.querySelectorAll('.stat-card');
                statCards.forEach((card, index) => {
                    setTimeout(() => {
                        card.style.opacity = '0';
                        card.style.transform = 'translateY(20px)';
                        card.style.transition = 'all 0.6s ease';

                        setTimeout(() => {
                            card.style.opacity = '1';
                            card.style.transform = 'translateY(0)';
                        }, 300);
                    }, index * 200);
                });
            });
        </script>
    </body>
    </html>
    """


@app.exception_handler(Exception)
async def page_not_found(_, exc):
    return HTMLResponse(
        f"<h1>404: Tâche introuvable ! Généralement une mauvaise entrée. <br><br>Erreur : {exc}</h1>",
        status_code=404,
    )