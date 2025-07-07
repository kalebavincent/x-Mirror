from aiofiles.os import remove, path as aiopath, makedirs
from asyncio import sleep
from functools import partial
from html import escape
from io import BytesIO
from os import getcwd
from time import time
from re import findall
from pytdbot.filters import create
from aioshutil import move

from .. import user_data, excluded_extensions, auth_chats, sudo_users
from ..core.config_manager import Config
from ..core.telegram_client import TgClient
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.media_utils import create_thumb
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.ext_utils.help_messages import user_settings_text
from ..helper.ext_utils.bot_utils import (
    update_user_ldata,
    new_task,
    get_size_bytes,
)
from ..helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    send_file,
    delete_message,
)

handler_dict = {}

leech_options = [
    "THUMBNAIL",
    "LEECH_SPLIT_SIZE",
    "LEECH_DUMP_CHAT",
    "LEECH_FILENAME_PREFIX",
    "THUMBNAIL_LAYOUT",
]
rclone_options = ["RCLONE_CONFIG", "RCLONE_PATH", "RCLONE_FLAGS"]
gdrive_options = ["TOKEN_PICKLE", "GDRIVE_ID", "INDEX_URL"]


async def get_user_settings(from_user, stype="main"):
    user_id = from_user.id
    name = f'<a href="tg://user?id={user_id}">{from_user.first_name}</a>'
    buttons = ButtonMaker()
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})

    if stype == "leech":
        thumbpath = f"thumbnails/{user_id}.jpg"
        buttons.data_button("Vignette", f"userset {user_id} menu THUMBNAIL")
        thumbmsg = "Existe" if await aiopath.exists(thumbpath) else "N'existe pas"
        buttons.data_button(
            "Taille de division Leech", f"userset {user_id} menu LEECH_SPLIT_SIZE"
        )
        if user_dict.get("LEECH_SPLIT_SIZE", False):
            split_size = user_dict["LEECH_SPLIT_SIZE"]
        else:
            split_size = Config.LEECH_SPLIT_SIZE
        buttons.data_button(
            "Destination Leech", f"userset {user_id} menu LEECH_DUMP_CHAT"
        )
        if user_dict.get("LEECH_DUMP_CHAT", False):
            leech_dest = user_dict["LEECH_DUMP_CHAT"]
        elif "LEECH_DUMP_CHAT" not in user_dict and Config.LEECH_DUMP_CHAT:
            leech_dest = Config.LEECH_DUMP_CHAT
        else:
            leech_dest = "Aucune"
        buttons.data_button(
            "Préfixe Leech", f"userset {user_id} menu LEECH_FILENAME_PREFIX"
        )
        if user_dict.get("LEECH_FILENAME_PREFIX", False):
            lprefix = user_dict["LEECH_FILENAME_PREFIX"]
        elif "LEECH_FILENAME_PREFIX" not in user_dict and Config.LEECH_FILENAME_PREFIX:
            lprefix = Config.LEECH_FILENAME_PREFIX
        else:
            lprefix = "Aucun"
        if (
            user_dict.get("AS_DOCUMENT", False)
            or "AS_DOCUMENT" not in user_dict
            and Config.AS_DOCUMENT
        ):
            ltype = "DOCUMENT"
            buttons.data_button("Envoyer en média", f"userset {user_id} tog AS_DOCUMENT f")
        else:
            ltype = "MÉDIA"
            buttons.data_button(
                "Envoyer en document", f"userset {user_id} tog AS_DOCUMENT t"
            )
        if (
            user_dict.get("EQUAL_SPLITS", False)
            or "EQUAL_SPLITS" not in user_dict
            and Config.EQUAL_SPLITS
        ):
            buttons.data_button(
                "Désactiver divisions égales", f"userset {user_id} tog EQUAL_SPLITS f"
            )
            equal_splits = "Activé"
        else:
            buttons.data_button(
                "Activer divisions égales", f"userset {user_id} tog EQUAL_SPLITS t"
            )
            equal_splits = "Désactivé"
        if (
            user_dict.get("MEDIA_GROUP", False)
            or "MEDIA_GROUP" not in user_dict
            and Config.MEDIA_GROUP
        ):
            buttons.data_button(
                "Désactiver groupe média", f"userset {user_id} tog MEDIA_GROUP f"
            )
            media_group = "Activé"
        else:
            buttons.data_button(
                "Activer groupe média", f"userset {user_id} tog MEDIA_GROUP t"
            )
            media_group = "Désactivé"
        if (
            TgClient.IS_PREMIUM_USER
            and user_dict.get("USER_TRANSMISSION", False)
            or "USER_TRANSMISSION" not in user_dict
            and Config.USER_TRANSMISSION
        ):
            buttons.data_button(
                "Leech par bot", f"userset {user_id} tog USER_TRANSMISSION f"
            )
            leech_method = "utilisateur"
        elif TgClient.IS_PREMIUM_USER:
            leech_method = "bot"
            buttons.data_button(
                "Leech par utilisateur", f"userset {user_id} tog USER_TRANSMISSION t"
            )
        else:
            leech_method = "bot"

        if (
            TgClient.IS_PREMIUM_USER
            and user_dict.get("HYBRID_LEECH", False)
            or "HYBRID_LEECH" not in user_dict
            and Config.HYBRID_LEECH
        ):
            hybrid_leech = "Activé"
            buttons.data_button(
                "Désactiver Leech hybride", f"userset {user_id} tog HYBRID_LEECH f"
            )
        elif TgClient.IS_PREMIUM_USER:
            hybrid_leech = "Désactivé"
            buttons.data_button(
                "Activer Leech hybride", f"userset {user_id} tog HYBRID_LEECH t"
            )
        else:
            hybrid_leech = "Désactivé"

        buttons.data_button(
            "Disposition vignette", f"userset {user_id} menu THUMBNAIL_LAYOUT"
        )
        if user_dict.get("THUMBNAIL_LAYOUT", False):
            thumb_layout = user_dict["THUMBNAIL_LAYOUT"]
        elif "THUMBNAIL_LAYOUT" not in user_dict and Config.THUMBNAIL_LAYOUT:
            thumb_layout = Config.THUMBNAIL_LAYOUT
        else:
            thumb_layout = "Aucune"

        buttons.data_button("Retour", f"userset {user_id} back")
        buttons.data_button("Fermer", f"userset {user_id} close")

        text = f"""<u>Paramètres Leech pour {name}</u>
Type Leech est <b>{ltype}</b>
Vignette personnalisée <b>{thumbmsg}</b>
Taille division Leech est <b>{split_size}</b>
Divisions égales <b>{equal_splits}</b>
Groupe média <b>{media_group}</b>
Préfixe Leech est <code>{escape(lprefix)}</code>
Destination Leech est <code>{leech_dest}</code>
Leech par session <b>{leech_method}</b>
Leech hybride <b>{hybrid_leech}</b>
Disposition vignette <b>{thumb_layout}</b>
"""
    elif stype == "rclone":
        buttons.data_button("Config Rclone", f"userset {user_id} menu RCLONE_CONFIG")
        buttons.data_button(
            "Chemin Rclone par défaut", f"userset {user_id} menu RCLONE_PATH"
        )
        buttons.data_button("Flags Rclone", f"userset {user_id} menu RCLONE_FLAGS")
        buttons.data_button("Retour", f"userset {user_id} back")
        buttons.data_button("Fermer", f"userset {user_id} close")
        rccmsg = "Existe" if await aiopath.exists(rclone_conf) else "N'existe pas"
        if user_dict.get("RCLONE_PATH", False):
            rccpath = user_dict["RCLONE_PATH"]
        elif Config.RCLONE_PATH:
            rccpath = Config.RCLONE_PATH
        else:
            rccpath = "Aucun"
        if user_dict.get("RCLONE_FLAGS", False):
            rcflags = user_dict["RCLONE_FLAGS"]
        elif "RCLONE_FLAGS" not in user_dict and Config.RCLONE_FLAGS:
            rcflags = Config.RCLONE_FLAGS
        else:
            rcflags = "Aucun"
        text = f"""<u>Paramètres Rclone pour {name}</u>
Config Rclone <b>{rccmsg}</b>
Chemin Rclone est <code>{rccpath}</code>
Flags Rclone est <code>{rcflags}</code>"""
    elif stype == "gdrive":
        buttons.data_button("token.pickle", f"userset {user_id} menu TOKEN_PICKLE")
        buttons.data_button("ID Gdrive par défaut", f"userset {user_id} menu GDRIVE_ID")
        buttons.data_button("URL Index", f"userset {user_id} menu INDEX_URL")
        if (
            user_dict.get("STOP_DUPLICATE", False)
            or "STOP_DUPLICATE" not in user_dict
            and Config.STOP_DUPLICATE
        ):
            buttons.data_button(
                "Désactiver doublons", f"userset {user_id} tog STOP_DUPLICATE f"
            )
            sd_msg = "Activé"
        else:
            buttons.data_button(
                "Activer doublons", f"userset {user_id} tog STOP_DUPLICATE t"
            )
            sd_msg = "Désactivé"
        buttons.data_button("Retour", f"userset {user_id} back")
        buttons.data_button("Fermer", f"userset {user_id} close")
        tokenmsg = "Existe" if await aiopath.exists(token_pickle) else "N'existe pas"
        if user_dict.get("GDRIVE_ID", False):
            gdrive_id = user_dict["GDRIVE_ID"]
        elif GDID := Config.GDRIVE_ID:
            gdrive_id = GDID
        else:
            gdrive_id = "Aucun"
        index = user_dict["INDEX_URL"] if user_dict.get("INDEX_URL", False) else "Aucun"
        text = f"""<u>Paramètres API Gdrive pour {name}</u>
Token Gdrive <b>{tokenmsg}</b>
ID Gdrive est <code>{gdrive_id}</code>
URL Index est <code>{index}</code>
Stop doublons <b>{sd_msg}</b>"""
    else:
        buttons.data_button("Leech", f"userset {user_id} leech")
        buttons.data_button("Rclone", f"userset {user_id} rclone")
        buttons.data_button("API Gdrive", f"userset {user_id} gdrive")

        upload_paths = user_dict.get("UPLOAD_PATHS", {})
        if not upload_paths and "UPLOAD_PATHS" not in user_dict and Config.UPLOAD_PATHS:
            upload_paths = Config.UPLOAD_PATHS
        else:
            upload_paths = "Aucun"

        buttons.data_button("Chemins d'upload", f"userset {user_id} menu UPLOAD_PATHS")

        if user_dict.get("DEFAULT_UPLOAD", ""):
            default_upload = user_dict["DEFAULT_UPLOAD"]
        elif "DEFAULT_UPLOAD" not in user_dict:
            default_upload = Config.DEFAULT_UPLOAD
        du = "API Gdrive" if default_upload == "gd" else "Rclone"
        dur = "API Gdrive" if default_upload != "gd" else "Rclone"
        buttons.data_button(
            f"Upload via {dur}", f"userset {user_id} {default_upload}"
        )

        user_tokens = user_dict.get("USER_TOKENS", False)
        tr = "MES" if user_tokens else "PROPRIÉTAIRE"
        trr = "PROPRIÉTAIRE" if user_tokens else "MES"
        buttons.data_button(
            f"Utiliser token/config {trr}",
            f"userset {user_id} tog USER_TOKENS {'f' if user_tokens else 't'}",
        )

        buttons.data_button(
            "Extensions exclues", f"userset {user_id} menu EXCLUDED_EXTENSIONS"
        )
        if user_dict.get("EXCLUDED_EXTENSIONS", False):
            ex_ex = user_dict["EXCLUDED_EXTENSIONS"]
        elif "EXCLUDED_EXTENSIONS" not in user_dict:
            ex_ex = excluded_extensions
        else:
            ex_ex = "Aucune"

        ns_msg = "Ajouté" if user_dict.get("NAME_SUBSTITUTE", False) else "Aucun"
        buttons.data_button("Substitution nom", f"userset {user_id} menu NAME_SUBSTITUTE")

        buttons.data_button("Options YT-DLP", f"userset {user_id} menu YT_DLP_OPTIONS")
        if user_dict.get("YT_DLP_OPTIONS", False):
            ytopt = user_dict["YT_DLP_OPTIONS"]
        elif "YT_DLP_OPTIONS" not in user_dict and Config.YT_DLP_OPTIONS:
            ytopt = Config.YT_DLP_OPTIONS
        else:
            ytopt = "Aucune"

        buttons.data_button("Commandes FFmpeg", f"userset {user_id} menu FFMPEG_CMDS")
        if user_dict.get("FFMPEG_CMDS", False):
            ffc = "Existe"
        elif "FFMPEG_CMDS" not in user_dict and Config.FFMPEG_CMDS:
            ffc = "Existe"
        else:
            ffc = "Aucune"

        if user_dict:
            buttons.data_button("Tout réinitialiser", f"userset {user_id} reset all")

        buttons.data_button("Fermer", f"userset {user_id} close")

        text = f"""<u>Paramètres pour {name}</u>
Package par défaut <b>{du}</b>
Utiliser token/config <b>{tr}</b>
Chemins d'upload <code>{upload_paths}</code>

Substitution nom <code>{ns_msg}</code>

Extensions exclues <code>{ex_ex}</code>

Options YT-DLP <code>{ytopt}</code>

Commandes FFMPEG <b>{ffc}</b>"""

    return text, buttons.build_menu(1)


async def update_user_settings(query, message, from_user, stype="main"):
    handler_dict[query.sender_user_id] = False
    msg, button = await get_user_settings(from_user, stype)
    await edit_message(message, msg, button)


@new_task
async def send_user_settings(_, message):
    from_user = message.getUser()
    handler_dict[message.from_id] = False
    msg, button = await get_user_settings(from_user)
    await send_message(message, msg, button)


@new_task
async def add_file(_, message, ftype):
    user_id = message.from_id
    handler_dict[user_id] = False
    if ftype == "THUMBNAIL":
        des_dir = await create_thumb(message, user_id)
    elif ftype == "RCLONE_CONFIG":
        rpath = f"{getcwd()}/rclone/"
        await makedirs(rpath, exist_ok=True)
        des_dir = f"{rpath}{user_id}.conf"
        res = await message.download(synchronous=True)
        await move(res.path, des_dir)
    elif ftype == "TOKEN_PICKLE":
        tpath = f"{getcwd()}/tokens/"
        await makedirs(tpath, exist_ok=True)
        des_dir = f"{tpath}{user_id}.pickle"
        res = await message.download(synchronous=True)
        await move(res.path, des_dir)
    update_user_ldata(user_id, ftype, des_dir)
    await delete_message(message)
    await database.update_user_doc(user_id, ftype, des_dir)


@new_task
async def add_one(_, message, option):
    user_id = message.from_id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    value = message.text
    if value.startswith("{") and value.endswith("}"):
        try:
            value = eval(value)
            if user_dict[option]:
                user_dict[option].update(value)
            else:
                update_user_ldata(user_id, option, value)
        except Exception as e:
            await send_message(message, str(e))
            return
    else:
        await send_message(message, "Doit être un dictionnaire !")
        return
    await delete_message(message)
    await database.update_user_data(user_id)


@new_task
async def remove_one(_, message, option):
    user_id = message.from_id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    names = message.text.split("/")
    for name in names:
        if name in user_dict[option]:
            del user_dict[option][name]
    await delete_message(message)
    await database.update_user_data(user_id)


@new_task
async def set_option(_, message, option):
    user_id = message.from_id
    handler_dict[user_id] = False
    value = message.text
    if option == "LEECH_SPLIT_SIZE":
        if not value.isdigit():
            value = get_size_bytes(value)
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    elif option == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    elif option in ["UPLOAD_PATHS", "FFMPEG_CMDS", "YT_DLP_OPTIONS"]:
        if value.startswith("{") and value.endswith("}"):
            try:
                value = eval(value)
            except Exception as e:
                await send_message(message, str(e))
                return
        else:
            await send_message(message, "Doit être un dictionnaire !")
            return
    update_user_ldata(user_id, option, value)
    await delete_message(message)
    await database.update_user_data(user_id)


async def get_menu(option, message, user_id):
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    buttons = ButtonMaker()
    if option in ["THUMBNAIL", "RCLONE_CONFIG", "TOKEN_PICKLE"]:
        key = "file"
    else:
        key = "set"
    buttons.data_button("Définir", f"userset {user_id} {key} {option}")
    if option in user_dict and key != "file":
        buttons.data_button("Réinitialiser", f"userset {user_id} reset {option}")
    buttons.data_button("Supprimer", f"userset {user_id} remove {option}")
    if option == "FFMPEG_CMDS":
        ffc = None
        if user_dict.get("FFMPEG_CMDS", False):
            ffc = user_dict["FFMPEG_CMDS"]
            buttons.data_button("Ajouter un", f"userset {user_id} addone {option}")
            buttons.data_button("Supprimer un", f"userset {user_id} rmone {option}")
        elif "FFMPEG_CMDS" not in user_dict and Config.FFMPEG_CMDS:
            ffc = Config.FFMPEG_CMDS
        if ffc:
            buttons.data_button("VARIABLES FFMPEG", f"userset {user_id} ffvar")
            buttons.data_button("Voir", f"userset {user_id} view {option}")
    elif option in user_dict and user_dict[option]:
        if option == "THUMBNAIL":
            buttons.data_button("Voir", f"userset {user_id} view {option}")
        elif option in ["YT_DLP_OPTIONS", "UPLOAD_PATHS"]:
            buttons.data_button("Ajouter un", f"userset {user_id} addone {option}")
            buttons.data_button("Supprimer un", f"userset {user_id} rmone {option}")
    if option in leech_options:
        back_to = "leech"
    elif option in rclone_options:
        back_to = "rclone"
    elif option in gdrive_options:
        back_to = "gdrive"
    else:
        back_to = "back"
    buttons.data_button("Retour", f"userset {user_id} {back_to}")
    buttons.data_button("Fermer", f"userset {user_id} close")
    text = f"Menu d'édition pour : {option}"
    await edit_message(message, text, buttons.build_menu(2))


async def set_ffmpeg_variable(_, message, key, value, index):
    user_id = message.from_id
    handler_dict[user_id] = False
    txt = message.text
    user_dict = user_data.setdefault(user_id, {})
    ffvar_data = user_dict.setdefault("FFMPEG_VARIABLES", {})
    ffvar_data = ffvar_data.setdefault(key, {})
    ffvar_data = ffvar_data.setdefault(index, {})
    ffvar_data[value] = txt
    await delete_message(message)
    await database.update_user_data(user_id)


async def ffmpeg_variables(
    client, query, message, user_id, key=None, value=None, index=None
):
    user_dict = user_data.get(user_id, {})
    ffc = None
    if user_dict.get("FFMPEG_CMDS", False):
        ffc = user_dict["FFMPEG_CMDS"]
    elif "FFMPEG_CMDS" not in user_dict and Config.FFMPEG_CMDS:
        ffc = Config.FFMPEG_CMDS
    if ffc:
        buttons = ButtonMaker()
        if key is None:
            msg = "Choisissez la clé à modifier :"
            for k, v in list(ffc.items()):
                add = False
                for l in v:
                    if variables := findall(r"\{(.*?)\}", l):
                        add = True
                if add:
                    buttons.data_button(k, f"userset {user_id} ffvar {k}")
            buttons.data_button("Retour", f"userset {user_id} menu FFMPEG_CMDS")
            buttons.data_button("Fermer", f"userset {user_id} close")
        elif key in ffc and value is None:
            msg = f"Choisissez la variable à modifier : <u>{key}</u>\n\nCOMMANDES :\n{ffc[key]}"
            for ind, vl in enumerate(ffc[key]):
                if variables := set(findall(r"\{(.*?)\}", vl)):
                    for var in variables:
                        buttons.data_button(
                            var, f"userset {user_id} ffvar {key} {var} {ind}"
                        )
            buttons.data_button(
                "Réinitialiser", f"userset {user_id} ffvar {key} ffmpegvarreset"
            )
            buttons.data_button("Retour", f"userset {user_id} ffvar")
            buttons.data_button("Fermer", f"userset {user_id} close")
        elif key in ffc and value:
            old_value = (
                user_dict.get("FFMPEG_VARIABLES", {})
                .get(key, {})
                .get(index, {})
                .get(value, "")
            )
            msg = f"Modifier cette variable FFmpeg : <u>{key}</u>\n\nÉlément : {ffc[key][int(index)]}\n\nVariable : {value}"
            if old_value:
                msg += f"\n\nValeur actuelle : {old_value}"
            buttons.data_button("Retour", f"userset {user_id} setevent")
            buttons.data_button("Fermer", f"userset {user_id} close")
        else:
            return
        await edit_message(message, msg, buttons.build_menu(2))
        if key in ffc and value:
            pfunc = partial(set_ffmpeg_variable, key=key, value=value, index=index)
            await event_handler(client, query, pfunc)
            await ffmpeg_variables(client, query, message, user_id, key)


async def event_handler(client, query, pfunc, photo=False, document=False):
    user_id = query.from_id
    handler_dict[user_id] = True
    start_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.content.photo
        elif document:
            mtype = event.content.document
        else:
            mtype = event.text
        return bool(
            event.from_id == user_id and event.chat_id == query.chat_id and mtype
        )

    client.add_handler(
        "updateNewMessage",
        pfunc,
        filters=create(event_filter),
        position=1,
        inner_object=True,
    )
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
    client.remove_handler(pfunc)


@new_task
async def edit_user_settings(client, query):
    user_id = query.sender_user_id
    from_user = await client.getUser(user_id)
    name = f'<a href="tg://user?id={user_id}">{from_user.first_name}</a>'
    message = await query.getMessage()
    data = query.text.split()
    handler_dict[user_id] = False
    thumb_path = f"thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        await query.answer("Ce n'est pas à vous !", show_alert=True)
    elif data[2] == "setevent":
        await query.answer()
    elif data[2] in ["leech", "gdrive", "rclone"]:
        await query.answer()
        await update_user_settings(query, message, from_user, data[2])
    elif data[2] == "menu":
        await query.answer()
        await get_menu(data[3], message, user_id)
    elif data[2] == "tog":
        await query.answer()
        update_user_ldata(user_id, data[3], data[4] == "t")
        if data[3] == "STOP_DUPLICATE":
            back_to = "gdrive"
        elif data[3] == "USER_TOKENS":
            back_to = "main"
        else:
            back_to = "leech"
        await update_user_settings(query, message, from_user, stype=back_to)
        await database.update_user_data(user_id)
    elif data[2] == "file":
        await query.answer()
        buttons = ButtonMaker()
        if data[3] == "THUMBNAIL":
            text = "Envoyez une photo comme vignette personnalisée. Délai : 60 sec"
        elif data[3] == "RCLONE_CONFIG":
            text = "Envoyez rclone.conf. Délai : 60 sec"
        else:
            text = "Envoyez token.pickle. Délai : 60 sec"
        buttons.data_button("Retour", f"userset {user_id} setevent")
        buttons.data_button("Fermer", f"userset {user_id} close")
        await edit_message(message, text, buttons.build_menu(1))
        pfunc = partial(add_file, ftype=data[3])
        await event_handler(
            client,
            query,
            pfunc,
            photo=data[3] == "THUMBNAIL",
            document=data[3] != "THUMBNAIL",
        )
        await get_menu(data[3], message, user_id)
    elif data[2] == "ffvar":
        await query.answer()
        key = data[3] if len(data) > 3 else None
        value = data[4] if len(data) > 4 else None
        if value == "ffmpegvarreset":
            user_dict = user_data.get(user_id, {})
            ff_data = user_dict.get("FFMPEG_VARIABLES", {})
            if key in ff_data:
                del ff_data[key]
                await database.update_user_data(user_id)
            return
        index = data[5] if len(data) > 5 else None
        await ffmpeg_variables(client, query, message, user_id, key, value, index)
    elif data[2] in ["set", "addone", "rmone"]:
        await query.answer()
        buttons = ButtonMaker()
        if data[2] == "set":
            text = user_settings_text[data[3]]
            func = set_option
        elif data[2] == "addone":
            text = f"Ajouter une ou plusieurs clés/valeurs à {data[3]}. Exemple : {{'clé 1': 62625261, 'clé 2': 'valeur 2'}}. Délai : 60 sec"
            func = add_one
        elif data[2] == "rmone":
            text = f"Supprimer une ou plusieurs clés de {data[3]}. Exemple : clé1/clé2/clé3. Délai : 60 sec"
            func = remove_one
        buttons.data_button("Retour", f"userset {user_id} setevent")
        buttons.data_button("Fermer", f"userset {user_id} close")
        await edit_message(message, text, buttons.build_menu(1))
        pfunc = partial(func, option=data[3])
        await event_handler(client, query, pfunc)
        await get_menu(data[3], message, user_id)
    elif data[2] == "remove":
        await query.answer("Supprimé !", show_alert=True)
        if data[3] in ["THUMBNAIL", "RCLONE_CONFIG", "TOKEN_PICKLE"]:
            if data[3] == "THUMBNAIL":
                fpath = thumb_path
            elif data[3] == "RCLONE_CONFIG":
                fpath = rclone_conf
            else:
                fpath = token_pickle
            if await aiopath.exists(fpath):
                await remove(fpath)
            del user_dict[data[3]]
            await database.update_user_doc(user_id, data[3])
        else:
            update_user_ldata(user_id, data[3], "")
            await database.update_user_data(user_id)
    elif data[2] == "reset":
        await query.answer("Réinitialisé !", show_alert=True)
        if data[3] in user_dict:
            del user_dict[data[3]]
        else:
            for k in list(user_dict.keys()):
                if k not in [
                    "SUDO",
                    "AUTH",
                    "THUMBNAIL",
                    "RCLONE_CONFIG",
                    "TOKEN_PICKLE",
                ]:
                    del user_dict[k]
            await update_user_settings(
                query,
                message,
                from_user,
            )
        await database.update_user_data(user_id)
    elif data[2] == "view":
        await query.answer()
        if data[3] == "THUMBNAIL":
            await send_file(message, thumb_path, name)
        elif data[3] == "FFMPEG_CMDS":
            ffc = None
            if user_dict.get("FFMPEG_CMDS", False):
                ffc = user_dict["FFMPEG_CMDS"]
            elif "FFMPEG_CMDS" not in user_dict and Config.FFMPEG_CMDS:
                ffc = Config.FFMPEG_CMDS
            msg_ecd = str(ffc).encode()
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await send_file(message, ofile)
    elif data[2] in ["gd", "rc"]:
        await query.answer()
        du = "rc" if data[2] == "gd" else "gd"
        update_user_ldata(user_id, "DEFAULT_UPLOAD", du)
        await update_user_settings(
            query,
            message,
            from_user,
        )
        await database.update_user_data(user_id)
    elif data[2] == "back":
        await query.answer()
        await update_user_settings(
            query,
            message,
            from_user,
        )
    else:
        await query.answer()
        reply_to = await message.getRepliedMessage()
        await delete_message(reply_to)
        await delete_message(message)


@new_task
async def get_users_settings(_, message):
    msg = ""
    if auth_chats:
        msg += f"CHATS AUTORISÉS : {auth_chats}\n"
    if sudo_users:
        msg += f"UTILISATEURS SUDO : {sudo_users}\n\n"
    if user_data:
        for u, d in user_data.items():
            kmsg = f"\n<b>{u}:</b>\n"
            if vmsg := "".join(
                f"{k}: <code>{v or None}</code>\n" for k, v in d.items()
            ):
                msg += kmsg + vmsg
        if not msg:
            await send_message(message, "Aucune donnée utilisateur !")
            return
        msg_ecd = msg.encode()
        if len(msg_ecd) > 4000:
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await send_file(message, ofile)
        else:
            await send_message(message, msg)
    else:
        await send_message(message, "Aucune donnée utilisateur !")