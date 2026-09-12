"""
Chargeur de plugins ARIA.

Un plugin est un dossier sous backend/plugins/<id>/ contenant :
  - manifest.json  : métadonnées (id, name, version, router_prefix, frontend, chat_handler,
                      lifecycle...)
  - router.py      : expose un objet FastAPI `router` (sans prefix, il est appliqué ici
                      à partir de `router_prefix` dans le manifest)
  - chat_handler.py (optionnel) : voir get_chat_handlers() plus bas
  - lifecycle.py    (optionnel) : voir get_lifecycle_hooks() plus bas — ajouté le 12/09/2026
                      pour plugins/messaging (lance/arrête whatsapp-bridge/ et telegram_bot.py
                      avec le backend)

L'état activé/désactivé de chaque plugin est persisté dans backend/data/plugins_state.json
(créé au premier démarrage avec les valeurs par défaut du manifest, `enabled_by_default`).
Un plugin désactivé n'est simplement pas monté au démarrage : FastAPI ne permet pas de
retirer un routeur déjà monté à chaud, donc (dés)activer un plugin via /api/plugins
nécessite un redémarrage du backend pour prendre effet (voir routes/plugins.py).
"""
import importlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).resolve().parent / "plugins"
STATE_PATH = Path(__file__).resolve().parent / "data" / "plugins_state.json"


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            logger.warning("plugins_state.json illisible (%s), état réinitialisé", error)
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def discover_plugins() -> list[dict]:
    """Liste les manifestes de tous les plugins présents sur disque (activés ou non).

    Chaque manifeste renvoyé porte en plus une clé interne "_dir" (nom du dossier), utilisée
    pour importer le module et retrouver le fichier — elle n'est pas censée être affichée.
    """
    manifests = []
    if not PLUGINS_DIR.exists():
        return manifests

    for entry in sorted(PLUGINS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        manifest_path = entry / "manifest.json"
        if not manifest_path.exists():
            logger.warning("Plugin '%s' ignoré : manifest.json manquant", entry.name)
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            logger.error("Plugin '%s' ignoré : manifest.json invalide (%s)", entry.name, error)
            continue
        manifest["_dir"] = entry.name
        manifests.append(manifest)
    return manifests


def list_plugin_status() -> list[dict]:
    """Version lecture seule de load_plugins() : ne monte aucun routeur.

    Utilisée par GET /api/plugins pour afficher l'état actuel sans dépendre de l'app FastAPI.
    """
    manifests = discover_plugins()
    state = _load_state()
    return [
        {**m, "enabled": state.get(m.get("id", m["_dir"]), m.get("enabled_by_default", True))}
        for m in manifests
    ]


def load_plugins(app) -> list[dict]:
    """Monte les routeurs REST des plugins activés sur `app` (appelé une fois au démarrage).

    Un plugin sans clé "router_prefix" dans son manifest n'a pas de routeur REST à monter
    (ex. un plugin chat_handler pur comme kings, voir get_chat_handlers ci-dessous) : il est
    quand même listé dans le résultat (utile pour /api/plugins), juste sans tentative
    d'import de plugins.<id>.router.

    Renvoie la liste des plugins trouvés avec leur état, y compris ceux en erreur de
    chargement (clé "load_error") — utile pour du diagnostic au démarrage.
    """
    manifests = discover_plugins()
    state = _load_state()
    changed = False
    result = []

    for manifest in manifests:
        plugin_id = manifest.get("id", manifest["_dir"])
        enabled = state.get(plugin_id)
        if enabled is None:
            enabled = manifest.get("enabled_by_default", True)
            state[plugin_id] = enabled
            changed = True

        entry = {**manifest, "enabled": enabled}
        result.append(entry)

        if not enabled:
            logger.info("Plugin '%s' désactivé, non chargé", plugin_id)
            continue

        router_prefix = manifest.get("router_prefix")
        if not router_prefix:
            logger.info("Plugin '%s' n'expose pas de routeur REST (chat_handler=%s)", plugin_id, manifest.get("chat_handler", False))
            continue

        module_name = f"plugins.{manifest['_dir']}.router"
        try:
            module = importlib.import_module(module_name)
            router = module.router
        except Exception as error:
            logger.error("Plugin '%s' : échec du chargement (%s)", plugin_id, error)
            entry["load_error"] = str(error)
            continue

        app.include_router(router, prefix=router_prefix, tags=[plugin_id])
        logger.info("Plugin '%s' monté sur %s", plugin_id, router_prefix)

    if changed:
        _save_state(state)

    return result


def get_chat_handlers() -> list[dict]:
    """Charge les handlers de chat des plugins activés qui en déclarent un
    (`"chat_handler": true` dans leur manifest, module plugins/<id>/chat_handler.py exposant
    `matches(message: str) -> bool` et `async def handle(message: str, context: dict) -> dict`).

    Indépendant de load_plugins(app) : n'a besoin que des manifestes + de l'état persisté, pas
    de l'app FastAPI. Fait pour être appelé une fois, à l'import de routes/chat.py — voir
    l'usage de PLUGIN_CHAT_HANDLERS là-bas. L'ordre (du plus prioritaire au moins prioritaire)
    vient de "chat_handler_order" dans le manifest (défaut 100) : le premier handler dont
    `matches()` renvoie True traite le message, les suivants ne sont pas essayés.
    """
    manifests = discover_plugins()
    state = _load_state()
    handlers = []

    for manifest in manifests:
        if not manifest.get("chat_handler"):
            continue
        plugin_id = manifest.get("id", manifest["_dir"])
        enabled = state.get(plugin_id, manifest.get("enabled_by_default", True))
        if not enabled:
            continue

        module_name = f"plugins.{manifest['_dir']}.chat_handler"
        try:
            module = importlib.import_module(module_name)
        except Exception as error:
            logger.error("Plugin '%s' : échec du chargement du chat_handler (%s)", plugin_id, error)
            continue

        name = manifest.get("name", plugin_id)
        handlers.append({
            "id": plugin_id,
            "name": name,
            "order": manifest.get("chat_handler_order", 100),
            "matches": module.matches,
            "handle": module.handle,
            "error_message": manifest.get("chat_error_message", f"{name} service unavailable"),
        })

    handlers.sort(key=lambda h: h["order"])
    return handlers


def get_lifecycle_hooks() -> list[dict]:
    """Charge les hooks de cycle de vie des plugins activés qui en déclarent un
    (`"lifecycle": true` dans leur manifest, module plugins/<id>/lifecycle.py exposant
    optionnellement `async def on_startup() -> None` et/ou `async def on_shutdown() -> None`).

    Même principe que get_chat_handlers() : indépendant de load_plugins(app), pensé pour être
    appelé une fois au démarrage du backend et une fois à l'arrêt (voir main.py, lifespan), en
    conservant la MÊME liste entre les deux (un hook peut garder un état en mémoire entre son
    on_startup et son on_shutdown, ex. un subprocess.Popen — voir plugins/messaging/lifecycle.py,
    premier exemple : lance whatsapp-bridge/ et telegram_bot.py avec le backend, les arrête
    avec lui)."""
    manifests = discover_plugins()
    state = _load_state()
    hooks = []

    for manifest in manifests:
        if not manifest.get("lifecycle"):
            continue
        plugin_id = manifest.get("id", manifest["_dir"])
        enabled = state.get(plugin_id, manifest.get("enabled_by_default", True))
        if not enabled:
            continue

        module_name = f"plugins.{manifest['_dir']}.lifecycle"
        try:
            module = importlib.import_module(module_name)
        except Exception as error:
            logger.error("Plugin '%s' : échec du chargement du hook de cycle de vie (%s)", plugin_id, error)
            continue

        hooks.append({
            "id": plugin_id,
            "on_startup": getattr(module, "on_startup", None),
            "on_shutdown": getattr(module, "on_shutdown", None),
        })

    return hooks


def set_plugin_enabled(plugin_id: str, enabled: bool) -> dict:
    """Persiste l'état d'un plugin. Ne prend effet qu'au prochain démarrage du backend."""
    manifests = {m.get("id", m["_dir"]): m for m in discover_plugins()}
    if plugin_id not in manifests:
        raise KeyError(plugin_id)

    state = _load_state()
    state[plugin_id] = enabled
    _save_state(state)
    return {"id": plugin_id, "enabled": enabled, "restart_required": True}
