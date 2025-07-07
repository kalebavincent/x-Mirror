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
    <meta name="description" content="Solution avancée pour le téléchargement, la conversion et la gestion de fichiers">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4361ee;
            --primary-hover: #3251e0;
            --secondary: #3f37c9;
            --accent: #4895ef;
            --accent-light: #5fa5ff;
            --dark: #0f172a;
            --darker: #0a1120;
            --light: #f8f9fa;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-bg-hover: rgba(40, 51, 69, 0.85);
            --success: #10b981;
            --warning: #f59e0b;
            --info: #3b82f6;
            --error: #ef4444;
            --gradient: linear-gradient(135deg, var(--primary), var(--secondary));
            --glass: rgba(30, 41, 59, 0.5);
            --transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at top left, #0f172a, #1e293b, #0a1120);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
            overflow-x: hidden;
        }

        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 10;
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
            background: var(--gradient);
            border-radius: 20px;
            align-items: center;
            justify-content: center;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(37, 99, 235, 0.4);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .logo::after {
            content: '';
            position: absolute;
            width: 150%;
            height: 150%;
            background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
            top: -25%;
            left: -25%;
            transform: rotate(30deg);
        }

        .logo:hover {
            transform: rotate(5deg) scale(1.05);
            box-shadow: 0 15px 40px rgba(37, 99, 235, 0.6);
        }

        .logo i {
            font-size: 3.5rem;
            color: white;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }

        .logo:hover i {
            transform: scale(1.1);
        }

        h1 {
            font-size: 3.2rem;
            margin-bottom: 15px;
            background: linear-gradient(90deg, #60a5fa, #3b82f6, #4895ef);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-weight: 800;
            letter-spacing: -0.5px;
            position: relative;
            display: inline-block;
        }

        h1::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            height: 4px;
            background: var(--gradient);
            border-radius: 2px;
        }

        .tagline {
            font-size: 1.4rem;
            max-width: 800px;
            margin: 0 auto 30px;
            color: #94a3b8;
            font-weight: 300;
            position: relative;
            padding: 0 20px;
        }

        .stats-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 25px;
            margin: 40px 0;
            max-width: 900px;
            margin: 40px auto;
        }

        .stat-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: var(--transition);
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--gradient);
        }

        .stat-card:hover {
            transform: translateY(-10px);
            background: var(--card-bg-hover);
            box-shadow: 0 12px 40px rgba(37, 99, 235, 0.3);
        }

        .stat-value {
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 10px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }

        .stat-label {
            font-size: 1.1rem;
            color: #cbd5e1;
            font-weight: 500;
            letter-spacing: 0.5px;
        }

        .roadmap-section {
            position: relative;
            padding: 50px 0;
            margin: 80px 0;
        }

        .section-title {
            text-align: center;
            font-size: 2.8rem;
            margin-bottom: 80px;
            position: relative;
            display: inline-block;
            left: 50%;
            transform: translateX(-50%);
            padding: 0 30px;
        }

        .section-title span {
            background: linear-gradient(90deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            position: relative;
            font-weight: 700;
        }

        .section-title::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent));
            bottom: -15px;
            left: 0;
            border-radius: 2px;
        }

        /* Nouvelle Timeline améliorée */
        .timeline {
            position: relative;
            max-width: 1100px;
            margin: 0 auto;
        }

        .timeline::after {
            content: '';
            position: absolute;
            width: 6px;
            background: linear-gradient(to bottom, var(--primary), var(--accent));
            top: 0;
            bottom: 0;
            left: 50%;
            margin-left: -3px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(67, 97, 238, 0.6);
        }

        .timeline-container {
            padding: 10px 50px;
            position: relative;
            width: 50%;
            opacity: 0;
            transform: translateY(30px);
            transition: all 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        .timeline-container.show {
            opacity: 1;
            transform: translateY(0);
        }

        .left {
            left: 0;
        }

        .right {
            left: 50%;
        }

        .timeline-card {
            padding: 35px;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            position: relative;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.25);
            transition: var(--transition);
            overflow: hidden;
        }

        .timeline-card:hover {
            transform: scale(1.02);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .timeline-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at top left, rgba(67, 97, 238, 0.1), transparent 70%);
            z-index: -1;
        }

        .timeline-card::after {
            content: '';
            position: absolute;
            border-width: 12px;
            border-style: solid;
            top: 35px;
        }

        .left::after {
            right: -24px;
            border-color: transparent transparent transparent var(--card-bg);
        }

        .right::after {
            left: -24px;
            border-color: transparent var(--card-bg) transparent transparent;
        }

        .timeline-container::before {
            content: '';
            position: absolute;
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border: 4px solid var(--darker);
            border-radius: 50%;
            top: 35px;
            z-index: 2;
            box-shadow: 0 0 15px rgba(67, 97, 238, 0.8);
        }

        .left::before {
            right: -15px;
        }

        .right::before {
            left: -15px;
        }

        .timeline-date {
            font-weight: 700;
            color: var(--accent-light);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            font-size: 1.2rem;
            text-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .timeline-date i {
            margin-right: 12px;
            font-size: 1.3rem;
            background: rgba(72, 149, 239, 0.2);
            width: 40px;
            height: 40px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
        }

        .timeline-card h3 {
            font-size: 1.7rem;
            margin-bottom: 20px;
            color: #fff;
            display: flex;
            align-items: center;
            text-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        .timeline-card h3 i {
            margin-right: 15px;
            width: 45px;
            height: 45px;
            background: rgba(67, 97, 238, 0.25);
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
        }

        .timeline-card ul {
            padding-left: 25px;
            color: #cbd5e1;
            font-size: 1.05rem;
        }

        .timeline-card li {
            margin-bottom: 15px;
            position: relative;
            padding-left: 15px;
            transition: transform 0.3s ease;
        }

        .timeline-card li:hover {
            transform: translateX(5px);
        }

        .timeline-card li::before {
            content: '•';
            color: var(--accent);
            font-weight: bold;
            font-size: 1.5rem;
            display: inline-block;
            width: 1em;
            margin-left: -1em;
            position: absolute;
            left: 0;
            top: -2px;
        }

        .progress-container {
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            margin-top: 20px;
            overflow: hidden;
        }

        .progress-bar {
            height: 100%;
            border-radius: 3px;
            transition: width 1.5s ease-out;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 8px 18px;
            border-radius: 30px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-top: 20px;
            backdrop-filter: blur(5px);
        }

        .status-planned {
            background: rgba(59, 130, 246, 0.25);
            color: var(--info);
        }

        .status-in-progress {
            background: rgba(245, 158, 11, 0.25);
            color: var(--warning);
        }

        .status-completed {
            background: rgba(16, 185, 129, 0.25);
            color: var(--success);
        }

        .cta-section {
            text-align: center;
            padding: 60px 0 40px;
            position: relative;
        }

        .cta-container {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 25px;
            max-width: 800px;
            margin: 0 auto;
        }

        .cta-button {
            display: inline-flex;
            align-items: center;
            padding: 18px 45px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            color: white;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.2rem;
            border-radius: 15px;
            transition: var(--transition);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
            border: none;
            cursor: pointer;
            position: relative;
            overflow: hidden;
            z-index: 1;
            min-width: 250px;
            justify-content: center;
        }

        .cta-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, var(--secondary), var(--primary));
            opacity: 0;
            transition: opacity 0.4s ease;
            z-index: -1;
        }

        .cta-button:hover {
            transform: translateY(-8px) scale(1.05);
            box-shadow: 0 12px 30px rgba(37, 99, 235, 0.7);
        }

        .cta-button:hover::before {
            opacity: 1;
        }

        .cta-button i {
            margin-right: 12px;
            font-size: 1.4rem;
            transition: transform 0.3s ease;
        }

        .cta-button:hover i {
            transform: scale(1.2);
        }

        .github {
            background: linear-gradient(90deg, #333, #24292e);
        }

        .github:hover {
            box-shadow: 0 12px 30px rgba(36, 41, 46, 0.7);
        }

        .github::before {
            background: linear-gradient(90deg, #24292e, #333);
        }

        .author {
            margin-top: 40px;
            padding-top: 40px;
            text-align: center;
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            color: #94a3b8;
            font-size: 1.2rem;
            position: relative;
        }

        .author::before {
            content: '';
            position: absolute;
            top: -1px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 2px;
            background: var(--gradient);
        }

        .author a {
            color: #60a5fa;
            text-decoration: none;
            font-weight: 700;
            transition: all 0.3s;
            position: relative;
        }

        .author a::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 0;
            height: 2px;
            background: #60a5fa;
            transition: width 0.3s ease;
        }

        .author a:hover {
            color: #93c5fd;
        }

        .author a:hover::after {
            width: 100%;
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-15px); }
            100% { transform: translateY(0px); }
        }

        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(67, 97, 238, 0.6); }
            70% { box-shadow: 0 0 0 15px rgba(67, 97, 238, 0); }
            100% { box-shadow: 0 0 0 0 rgba(67, 97, 238, 0); }
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        @media (max-width: 992px) {
            .timeline::after {
                left: 40px;
            }

            .timeline-container {
                width: 100%;
                padding-left: 80px;
                padding-right: 30px;
            }

            .right {
                left: 0;
            }

            .left::after, .right::after {
                left: 28px;
                border-color: transparent var(--card-bg) transparent transparent;
            }

            .left::before, .right::before {
                left: 28px;
            }
        }

        @media (max-width: 768px) {
            h1 { font-size: 2.5rem; }
            .tagline { font-size: 1.2rem; }
            .section-title { font-size: 2.3rem; }
            .stat-card { padding: 20px; }
            .stat-value { font-size: 2.3rem; }
            .timeline-card { padding: 25px; }
            .cta-button { min-width: 100%; margin-bottom: 15px; }
        }

        @media (max-width: 480px) {
            h1 { font-size: 2rem; }
            .section-title { font-size: 1.8rem; }
            .tagline { font-size: 1.1rem; }
            .stat-card { padding: 15px; }
            .stat-value { font-size: 2rem; }
            .timeline-date { font-size: 1.1rem; }
            .timeline-card h3 { font-size: 1.4rem; }
        }
    </style>
</head>
<body>
    <div class="particles" id="particles"></div>
    
    <div class="container">
        <header>
            <div class="logo pulse">
                <i class="fas fa-robot"></i>
            </div>
            <h1>Mirror-Leech Bot</h1>
            <p class="tagline">
                Solution tout-en-un pour télécharger, convertir et gérer vos fichiers avec une efficacité maximale
            </p>

            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-value">20+</div>
                    <div class="stat-label">Plateformes supportées</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">100K+</div>
                    <div class="stat-label">Utilisateurs actifs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">24/7</div>
                    <div class="stat-label">Disponibilité globale</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">2026</div>
                    <div class="stat-label">Roadmap ambitieuse</div>
                </div>
            </div>
        </header>

        <section class="roadmap-section">
            <h2 class="section-title">🚀 <span>Roadmap 2026</span></h2>

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
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 65%; background: var(--warning);"></div>
                        </div>
                        <div class="status-badge status-in-progress">
                            <i class="fas fa-sync-alt fa-spin"></i> En développement
                        </div>
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
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 15%; background: var(--info);"></div>
                        </div>
                        <div class="status-badge status-planned">
                            <i class="fas fa-clock"></i> Planifié
                        </div>
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
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 5%; background: var(--info);"></div>
                        </div>
                        <div class="status-badge status-planned">
                            <i class="fas fa-clock"></i> Planifié
                        </div>
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
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 0%; background: var(--info);"></div>
                        </div>
                        <div class="status-badge status-planned">
                            <i class="fas fa-clock"></i> Planifié
                        </div>
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
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 100%; background: var(--success);"></div>
                        </div>
                        <div class="status-badge status-completed">
                            <i class="fas fa-check-circle"></i> Complété
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <div class="cta-section">
            <div class="cta-container">
                <a href="https://t.me/hyoshcoder" class="cta-button">
                    <i class="fab fa-telegram"></i> Rejoindre sur Telegram
                </a>
                <a href="https://github.com/hyoshcoder" class="cta-button github">
                    <i class="fab fa-github"></i> Voir sur GitHub
                </a>
                <a href="#" class="cta-button" style="background: linear-gradient(90deg, #8B5CF6, #EC4899);">
                    <i class="fas fa-download"></i> Télécharger l'App
                </a>
            </div>
        </div>

        <div class="author">
            Développé avec <i class="fas fa-heart" style="color: #ef4444;"></i> par
            <a href="https://t.me/hyoshcoder">Hyosh Coder</a> &copy; 2026 - Tous droits réservés
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Animation des particules
            particlesJS('particles', {
                particles: {
                    number: { value: 60, density: { enable: true, value_area: 800 } },
                    color: { value: "#4895ef" },
                    shape: { type: "circle" },
                    opacity: { value: 0.1, random: true },
                    size: { value: 3, random: true },
                    line_linked: {
                        enable: true,
                        distance: 150,
                        color: "#3b82f6",
                        opacity: 0.05,
                        width: 1
                    },
                    move: {
                        enable: true,
                        speed: 1,
                        direction: "none",
                        random: true,
                        straight: false,
                        out_mode: "out",
                        bounce: false
                    }
                },
                interactivity: {
                    detect_on: "canvas",
                    events: {
                        onhover: { enable: true, mode: "repulse" },
                        onclick: { enable: true, mode: "push" },
                        resize: true
                    }
                },
                retina_detect: true
            });

            // Animation de la timeline
            const timelineContainers = document.querySelectorAll('.timeline-container');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('show');
                        
                        // Animation des barres de progression
                        const progressBar = entry.target.querySelector('.progress-bar');
                        if (progressBar) {
                            const width = progressBar.style.width;
                            progressBar.style.width = '0';
                            setTimeout(() => {
                                progressBar.style.transition = 'width 1.5s ease-out';
                                progressBar.style.width = width;
                            }, 300);
                        }
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
                    card.style.transform = 'translateY(30px) scale(0.95)';
                    card.style.transition = 'all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0) scale(1)';
                    }, 300);
                }, index * 200);
            });

            // Effet de flottement pour le logo
            const logo = document.querySelector('.logo');
            setInterval(() => {
                logo.style.animation = 'float 3s ease-in-out infinite';
            }, 4000);
        });
    </script>
</body>
</html>
"""


@app.exception_handler(Exception)
async def page_not_found(_, exc):
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>404 - Tâche introuvable</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            background: radial-gradient(circle at top left, #0f172a, #1e293b, #0a1120);
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .error-container {
            background: rgba(30, 41, 59, 0.85);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(37, 99, 235, 0.2);
            padding: 50px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 4rem;
            color: #ef4444;
            margin-bottom: 20px;
            animation: pulse 1.5s infinite;
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 15px;
            background: linear-gradient(90deg, #60a5fa, #3b82f6, #4895ef);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-weight: 800;
        }
        .desc {
            color: #94a3b8;
            margin-bottom: 25px;
            font-size: 1.15rem;
        }
        .error-detail {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 20px;
            font-size: 1rem;
            word-break: break-all;
        }
        a.home-link {
            display: inline-block;
            margin-top: 10px;
            padding: 12px 30px;
            background: linear-gradient(90deg, #4361ee, #3f37c9);
            color: #fff;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.1rem;
            transition: background 0.3s, transform 0.3s;
        }
        a.home-link:hover {
            background: linear-gradient(90deg, #3f37c9, #4361ee);
            transform: translateY(-3px) scale(1.04);
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
            70% { box-shadow: 0 0 0 18px rgba(239,68,68,0); }
            100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="error-container">
        <div class="error-icon"><i class="fas fa-exclamation-triangle"></i></div>
        <h1>404 : Tâche introuvable !</h1>
        <div class="desc">
            Généralement une mauvaise entrée.<br>
            Veuillez vérifier votre requête ou réessayer plus tard.
        </div>
        <div class="error-detail">{}</div>
        <a href="/" class="home-link"><i class="fas fa-home"></i> Retour à l'accueil</a>
    </div>
</body>
</html>
        """.format(str(exc)),
        status_code=404,
    )