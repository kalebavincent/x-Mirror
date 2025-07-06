from ..telegram_helper.bot_commands import BotCommands
from ...core.telegram_client import TgClient

mirror = """<b>Envoyez le lien avec la ligne de commande ou </b>

/cmd lien

<b>En répondant à un lien/fichier</b>:

/cmd -n nouveau nom -e -up destination d'upload

<b>NOTE:</b>
1. Les commandes commençant par <b>qb</b> sont UNIQUEMENT pour les torrents."""

yt = """<b>Envoyez le lien avec la ligne de commande</b>:

/cmd lien
<b>En répondant à un lien</b>:
/cmd -n nouveau nom -z motdepasse -opt x:y|x1:y1

Voir tous les <a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>SITES supportés</a>
Voir toutes les options yt-dlp dans ce <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L212'>FICHIER</a> ou utilisez ce <a href='https://t.me/hyoshcoder/mltb_official_channel/177'>script</a> pour convertir les arguments CLI en options API."""

clone = """Envoyez un lien Gdrive|Gdot|Filepress|Filebee|Appdrive|Gdflix ou un chemin rclone avec la commande ou en répondant au lien/chemin_rc.
Utilisez -sync pour utiliser la méthode sync dans rclone. Exemple: /cmd rcl/chemin_rclone -up rcl/chemin_rclone/rc -sync"""

new_name = """<b>Nouveau nom</b>: -n

/cmd lien -n nouveau nom
Note: Ne fonctionne pas avec les torrents"""

multi_link = """<b>Liens multiples uniquement en répondant au premier lien/fichier</b>: -i

/cmd -i 10(nombre de liens/fichiers)"""

same_dir = """<b>Déplacer des fichiers/dossiers vers un nouveau dossier</b>: -m

Vous pouvez utiliser cet argument pour déplacer le contenu de plusieurs liens/torrents vers le même dossier, ainsi tous les liens seront uploadés ensemble comme une seule tâche

/cmd lien -m nouveau dossier (un seul lien dans le nouveau dossier)
/cmd -i 10(nombre de liens/fichiers) -m nom du dossier (tout le contenu dans un dossier)
/cmd -b -m nom du dossier (réponse à un lot de messages/fichiers)

Avec le mode bulk, vous pouvez utiliser cet argument avec différents noms de dossiers
Exemple:
lien1 -m dossier1
lien2 -m dossier1
lien3 -m dossier2
lien4 -m dossier2
lien5 -m dossier3
lien6
→ lien1 et lien2 seront uploadés depuis dossier1
→ lien3 et lien4 depuis dossier2
→ lien5 seul dans dossier3
→ lien6 normalement seul
"""

thumb = """<b>Miniature pour la tâche actuelle</b>: -t

/cmd lien -t lien-message-tg (doc ou photo) ou none (fichier sans miniature)"""

split_size = """<b>Taille de division pour la tâche actuelle</b>: -sp

/cmd lien -sp (500mo ou 2go ou 4000000000)
Note: Seuls mo et go sont supportés ou indiquez en octets sans unité !"""

upload = """<b>Destination d'upload</b>: -up

/cmd lien -up rcl/gdl (rcl: sélection config rclone | gdl: sélection token.pickle) via boutons
Vous pouvez ajouter directement le chemin : -up remote:dossier/sousdossier ou -up Gdrive_id ou -up id/username (telegram) ou -up id/username|topic_id (telegram)
Si DEFAULT_UPLOAD est `rc`, utilisez up: `gd` pour uploader vers GDRIVE_ID.
Si DEFAULT_UPLOAD est `gd`, utilisez up: `rc` pour uploader vers RCLONE_PATH.

Pour ajouter manuellement un chemin/config : préfixez avec mrcc: (rclone) ou mtp: (gdrive)
/cmd lien -up mrcc:main:dump ou -up mtp:gdrive_id

Pour une destination leech :
-up id/@username/pm
-up b:id/@username/pm (b: leech par le bot)
-up u:id/@username (u: leech par l'utilisateur)
-up h:id/@username (hybride selon taille)
-up id/@username|topic_id (dans un topic spécifique)"""

user_download = """<b>Téléchargement utilisateur</b>: lien

/cmd tp:lien → utiliser token.pickle propriétaire
/cmd sa:lien → utiliser service account
/cmd mtp:lien → utiliser token.pickle utilisateur
/cmd mrcc:remote:chemin → utiliser config rclone utilisateur"""

rcf = """<b>Flags Rclone</b>: -rcf

/cmd lien|chemin|rcl -up chemin|rcl -rcf --buffer-size:8M|--drive-starred-only|clé|clé:valeur
Voir tous les <a href='https://rclone.org/flags/'>RcloneFlags</a>."""

bulk = """<b>Téléchargement en masse</b>: -b

Utilisable uniquement en répondant à un message/fichier texte avec liens séparés par des retours à la ligne.
Exemple:
lien1 -n nouveau nom -up remote1:chemin1 -rcf |clé:valeur|clé:valeur
lien2 -z -n nouveau nom -up remote2:chemin2
lien3 -e -n nouveau nom -up remote2:chemin2
Répondez avec : /cmd -b

Note: Tout argument avec la commande s'appliquera à tous les liens
/cmd -b -up remote: -z -m nom_dossier (tout dans un dossier zippé)
Utilisez -b début:fin pour spécifier une plage de liens."""

rlone_dl = """<b>Téléchargement Rclone</b>:

Traitez les chemins rclone comme des liens
/cmd main:dump/ubuntu.iso ou rcl (sélection via boutons)
Pour utiliser votre config : /cmd mrcc:main:dump/ubuntu.iso"""

extract_zip = """<b>Extraire/Zipper</b>: -e -z

/cmd lien -e motdepasse (extraire protégé)
/cmd lien -z motdepasse (zipper protégé)
/cmd lien -z motdepasse -e (extraire puis zipper)
Note: L'extraction se fait toujours avant le zip"""

join = """<b>Joindre les fichiers divisés</b>: -j

Utilisable avec -m (même dossier)
Exemples:
/cmd -i 3 -j -m nom_dossier
/cmd -b -j -m nom_dossier
Pour un lien de dossier avec fichiers divisés:
/cmd lien -j"""

tg_links = """<b>Liens Telegram</b>:

Traitez les liens TG comme des liens directs
Trois types de liens :
Public: https://t.me/hyoshcoder/nom_canal/id_message
Privé: tg://openmessage?user_id=xxxxxx&message_id=xxxxx
Super: https://t.me/hyoshcoder/c/id_canal/id_message
Plage: https://t.me/hyoshcoder/nom_canal/premier_id-dernier_id
Note: Les liens de plage ne fonctionnent qu'en réponse"""

sample_video = """<b>Échantillon vidéo</b>: -sv

Crée un échantillon vidéo.
/cmd -sv (valeurs par défaut: 60s durée, 4s partie)
Exemples: /cmd -sv 70:5 ou /cmd -sv :5 ou /cmd -sv 70."""

screenshot = """<b>Captures d'écran</b>: -ss

Crée des captures pour une vidéo/dossier.
/cmd -ss (10 photos par défaut)
Exemple: /cmd -ss 6."""

seed = """<b>Seed Bittorrent</b>: -d

/cmd lien -d ratio:temps_seed ou en réponse
Exemples: -d 0.7:10 (ratio et temps) ou -d 0.7 (ratio seul) ou -d :10 (temps seul)"""

zip_arg = """<b>Zip</b>: -z motdepasse

/cmd lien -z (zip simple)
/cmd lien -z motdepasse (zip protégé)"""

qual = """<b>Boutons de qualité</b>: -s

Pour sélectionner la qualité spécifiquement
/cmd lien -s"""

yt_opt = """<b>Options</b>: -opt

/cmd lien -opt {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, ...}
Voir les options dans ce <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FICHIER</a>"""

convert_media = """<b>Convertir les médias</b>: -ca -cv
/cmd lien -ca mp3 -cv mp4 (convertir audios en mp3 et vidéos en mp4)
/cmd lien -ca mp3 (convertir tous les audios en mp3)
/cmd lien -cv mp4 (convertir toutes les vidéos en mp4)
/cmd lien -ca mp3 + flac ogg (convertir uniquement flac/ogg en mp3)
/cmd lien -cv mkv - webm flv (convertir en mp4 sauf webm/flv)"""

force_start = """<b>Forcer le démarrage</b>: -f -fd -fu
/cmd lien -f (forcer téléchargement + upload)
/cmd lien -fd (forcer téléchargement seulement)
/cmd lien -fu (forcer upload après téléchargement)"""

gdrive = """<b>Gdrive</b>: lien
Si DEFAULT_UPLOAD est `rc`, utilisez up: `gd` pour uploader vers GDRIVE_ID.
Exemples:
/cmd lienGdrive ou gdl ou idGdrive -up gdl ou idGdrive ou gd
/cmd tp:lienGdrive -up tp:idGdrive (utiliser token.pickle)
/cmd sa:lienGdrive -up sa:idGdrive (utiliser service account)
/cmd mtp:lienGdrive -up mtp:idGdrive (utiliser token utilisateur)"""

rclone_cl = """<b>Rclone</b>: chemin
Si DEFAULT_UPLOAD est `gd`, utilisez up: `rc` pour uploader vers RCLONE_PATH.
Exemples:
/cmd rcl ou chemin_rclone -up chemin_rclone ou rc ou rcl
/cmd mrcc:chemin_rclone -up rcl (utiliser config utilisateur)"""

name_sub = r"""<b>Substitution de nom</b>: -ns
/cmd lien -ns texte_original/texte_remplacement/sensible
Exemple: script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[mltb\]/mltb | \\text\\/text/s
Timeout: 60 sec
Note: Échapper les caractères spéciaux : \^$.|?*+()[]{}-"""

transmission = """<b>Transmission TG</b>: -hl -ut -bt
/cmd lien -hl (leech hybride bot/utilisateur)
/cmd lien -bt (leech par bot)
/cmd lien -ut (leech par utilisateur)"""

thumbnail_layout = """Disposition des miniatures: -tl
/cmd lien -tl 3x3 (largeurxhauteur)"""

leech_as = """<b>Type de leech</b>: -doc -med
/cmd lien -doc (comme document)
/cmd lien -med (comme media)"""

ffmpeg_cmds = """<b>Commandes FFmpeg</b>: -ff
Listes de commandes FFmpeg à exécuter avant l'upload.
Notes:
1. Ajoutez <code>-del</code> pour supprimer les originaux
2. Utilisez "mltb" comme référence aux fichiers
Exemples:
["-i mltb.mkv -c copy -c:s srt mltb.mkv",
"-i mltb.video -c copy -c:s srt mltb",
"-i mltb -i tg://... -filter_complex 'overlay=W-w-10:H-h-10' -c:a copy mltb"]"""

YT_HELP_DICT = {
    "main": yt,
    "New-Name": f"{new_name}\nNote: Ne pas ajouter d'extension de fichier",
    "Zip": zip_arg,
    "Quality": qual,
    "Options": yt_opt,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,
    "Name-Substitute": name_sub,
    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "FFmpeg-Cmds": ffmpeg_cmds,
}

MIRROR_HELP_DICT = {
    "main": mirror,
    "New-Name": new_name,
    "DL-Auth": "<b>Authentification lien direct</b>: -au -ap\n\n/cmd lien -au utilisateur -ap motdepasse",
    "Headers": "<b>En-têtes personnalisés</b>: -h\n\n/cmd lien -h clé:valeur|clé1:valeur1",
    "Extract/Zip": extract_zip,
    "Select-Files": "<b>Sélection de fichiers</b>: -s\n\n/cmd lien -s ou en réponse",
    "Torrent-Seed": seed,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Join": join,
    "Rclone-DL": rlone_dl,
    "Tg-Links": tg_links,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,
    "User-Download": user_download,
    "Name-Substitute": name_sub,
    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "FFmpeg-Cmds": ffmpeg_cmds,
}

CLONE_HELP_DICT = {
    "main": clone,
    "Multi-Link": multi_link,
    "Bulk": bulk,
    "Gdrive": gdrive,
    "Rclone": rclone_cl,
}

RSS_HELP_MESSAGE = """
Format pour ajouter un flux RSS :
Titre1 lien (obligatoire)
Titre2 lien -c cmd -inf xx -exf xx
Titre3 lien -c cmd -d ratio:temps -z motdepasse

Options :
-c commande -up mrcc:remote:chemin -rcf flags
-inf Filtre mots inclus
-exf Filtre mots exclus
-stv true/false (filtre sensible)

Exemple: Titre https://www.rss-url.com -inf 1080|720|144p mkv|mp4 hevc -exf flv|web xxx
→ Analyse les titres contenant (1080 OU 720 OU 144p) ET (mkv OU mp4) ET hevc, excluant flv OU web OU xxx.

Notes filtres :
1. | = ET
2. Utilisez "ou" entre clés similaires
Timeout: 60 sec.
"""

PASSWORD_ERROR_MESSAGE = """
<b>Ce lien nécessite un mot de passe !</b>
- Insérez <b>::</b> après le lien puis le mot de passe.

<b>Exemple:</b> lien::mon motdepasse
"""

user_settings_text = {
    "LEECH_SPLIT_SIZE": f"Taille de division Leech (octets, go, mo). Ex: 40000000 ou 2.5go ou 1000mo. IS_PREMIUM_USER: {TgClient.IS_PREMIUM_USER}. Timeout: 60 sec",
    "LEECH_DUMP_CHAT": """Destination Leech ID/USERNAME/PM.
* b:id/@username/pm (leech par bot)
* u:id/@username (leech par utilisateur)
* h:id/@username (hybride)
* id/@username|topic_id (dans un topic)
Timeout: 60 sec""",
    "LEECH_FILENAME_PREFIX": r"Préfixe des noms de fichiers Leech. Balises HTML autorisées. Ex: <code>@machaine</code>. Timeout: 60 sec",
    "THUMBNAIL_LAYOUT": "Disposition miniatures (largeurxhauteur). Ex: 3x3. Timeout: 60 sec",
    "RCLONE_PATH": "Chemin Rclone. Pour votre config : mrcc:remote:dossier. Timeout: 60 sec",
    "RCLONE_FLAGS": "clé:valeur|clé|clé|clé:valeur. Voir <a href='https://rclone.org/flags/'>RcloneFlags</a>",
    "GDRIVE_ID": "ID Gdrive. Pour votre token : mtp:F435RGGRDXXXXXX. Timeout: 60 sec",
    "INDEX_URL": "URL Index. Timeout: 60 sec",
    "UPLOAD_PATHS": "Dict des chemins. Ex: {'chemin 1': 'remote:dossier', 'chemin 2': 'gdrive_id', 'chemin 3': 'tg_id', 'chemin 4': 'mrcc:remote:', 'chemin 5': 'b:@username'}. Timeout: 60 sec",
    "EXCLUDED_EXTENSIONS": "Extensions exclues (sans point). Timeout: 60 sec",
    "NAME_SUBSTITUTE": r"""Substitution de mots. Timeout: 60 sec
Ex: script/code/s | mirror/leech | tea/ /s | clone | cpu/ | \[mltb\]/mltb | \\text\\/text/s
Note: Échapper \^$.|?*+()[]{}-""",
    "YT_DLP_OPTIONS": """Dict d'options YT-DLP. Timeout: 60 sec
Ex: {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, ...}
Voir <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FICHIER</a>""",
    "FFMPEG_CMDS": """Dict de listes de commandes FFmpeg.
Ex: {"subtitle": ["-i mltb.mkv -c copy -c:s srt mltb.mkv", ...], "watermark": ["-i mltb -i lien_tg -filter_complex ..."]}
Notes:
- Ajoutez `-del` pour supprimer les originaux
- Utilisez "mltb" comme référence aux fichiers
- Variables disponibles dans metadata: {title}, {title2}, etc.""",
}


help_string = f"""
NOTE: Essayez chaque commande sans argument pour plus de détails.
/{BotCommands.MirrorCommand[0]} ou /{BotCommands.MirrorCommand[1]}: Mirroring vers le cloud.
/{BotCommands.QbMirrorCommand[0]} ou /{BotCommands.QbMirrorCommand[1]}: Mirroring avec qBittorrent.
/{BotCommands.JdMirrorCommand[0]} ou /{BotCommands.JdMirrorCommand[1]}: Mirroring avec JDownloader.
/{BotCommands.NzbMirrorCommand[0]} ou /{BotCommands.NzbMirrorCommand[1]}: Mirroring avec Sabnzbd.
/{BotCommands.YtdlCommand[0]} ou /{BotCommands.YtdlCommand[1]}: Mirror lien supporté par yt-dlp.
/{BotCommands.LeechCommand[0]} ou /{BotCommands.LeechCommand[1]}: Leech vers Telegram.
/{BotCommands.QbLeechCommand[0]} ou /{BotCommands.QbLeechCommand[1]}: Leech avec qBittorrent.
/{BotCommands.JdLeechCommand[0]} ou /{BotCommands.JdLeechCommand[1]}: Leech avec JDownloader.
/{BotCommands.NzbLeechCommand[0]} ou /{BotCommands.NzbLeechCommand[1]}: Leech avec Sabnzbd.
/{BotCommands.YtdlLeechCommand[0]} ou /{BotCommands.YtdlLeechCommand[1]}: Leech lien yt-dlp.
/{BotCommands.CloneCommand} [lien_drive]: Copier vers Google Drive.
/{BotCommands.CountCommand} [lien_drive]: Compter fichiers/dossiers Google Drive.
/{BotCommands.DeleteCommand} [lien_drive]: Supprimer de Google Drive (Propriétaire/Sudo).
/{BotCommands.UserSetCommand[0]} ou /{BotCommands.UserSetCommand[1]} [query]: Paramètres utilisateur.
/{BotCommands.BotSetCommand[0]} ou /{BotCommands.BotSetCommand[1]} [query]: Paramètres du bot.
/{BotCommands.SelectCommand}: Sélectionner fichiers torrents/nzb par gid ou réponse.
/{BotCommands.CancelTaskCommand[0]} ou /{BotCommands.CancelTaskCommand[1]} [gid]: Annuler tâche par gid.
/{BotCommands.ForceStartCommand[0]} ou /{BotCommands.ForceStartCommand[1]} [gid]: Forcer démarrage par gid.
/{BotCommands.CancelAllCommand} [query]: Annuler toutes les tâches [statut].
/{BotCommands.ListCommand} [query]: Rechercher dans Google Drive(s).
/{BotCommands.SearchCommand} [query]: Rechercher torrents via API.
/{BotCommands.StatusCommand}: Statut de tous les téléchargements.
/{BotCommands.StatsCommand}: Statistiques de la machine hôte.
/{BotCommands.PingCommand}: Ping du bot (Propriétaire/Sudo).
/{BotCommands.AuthorizeCommand}: Autoriser un chat/utilisateur (Propriétaire/Sudo).
/{BotCommands.UnAuthorizeCommand}: Désautoriser (Propriétaire/Sudo).
/{BotCommands.UsersCommand}: Voir paramètres utilisateurs (Propriétaire/Sudo).
/{BotCommands.AddSudoCommand}: Ajouter sudo (Propriétaire).
/{BotCommands.RmSudoCommand}: Supprimer sudo (Propriétaire).
/{BotCommands.RestartCommand}: Redémarrer/mettre à jour le bot (Propriétaire/Sudo).
/{BotCommands.LogCommand}: Obtenir les logs (Propriétaire/Sudo).
/{BotCommands.ShellCommand}: Exécuter commandes shell (Propriétaire).
/{BotCommands.AExecCommand}: Exécuter fonctions async (Propriétaire).
/{BotCommands.ExecCommand}: Exécuter fonctions sync (Propriétaire).
/{BotCommands.ClearLocalsCommand}: Effacer variables {BotCommands.AExecCommand}/{BotCommands.ExecCommand} (Propriétaire).
/{BotCommands.RssCommand}: Menu RSS.
"""