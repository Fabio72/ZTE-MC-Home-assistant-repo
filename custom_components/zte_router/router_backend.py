import logging
from typing import Optional

from . import mc
from .const import (
    ROUTER_TYPE_G5_ULTRA,
    ROUTER_TYPE_MC888,
    # FORK LOCALE -- potatura MC888 (vedi .ha_patch/zte-fork/docs/plan.md).
    # Il profilo dei parametri richiesti al router vive in const.py: qui si
    # decide solo *quando* applicarlo (MC888), mc.py non importa .const per
    # restare eseguibile standalone come script.
    MC888_PRUNE_ENABLED,
    MC888_ZTEINFO3_GROUPS,
)
from .g5_ultra_client import G5UltraRouterRunner

LOGGER = logging.getLogger(__name__)


def run_router_commands(
    router_type: str,
    ip: str,
    password: str,
    username: Optional[str],
    commands: str,
    phone_number: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """Execute router commands using the appropriate backend."""
    if router_type == ROUTER_TYPE_G5_ULTRA:
        runner = G5UltraRouterRunner(ip, password)
        return runner.run_commands(commands, phone=phone_number, message=message)
    return _run_mc_commands(router_type, ip, password, username, commands, phone_number, message)


def _run_mc_commands(
    router_type: str,
    ip: str,
    password: str,
    username: Optional[str],
    commands: str,
    phone_number: Optional[str],
    message: Optional[str],
) -> str:
    """Run MC-series commands in-process via zteRouter (mc.py)."""
    LOGGER.debug("Executing MC router command(s): %s", commands)
    # FORK LOCALE -- profilo minimo MC888: mc.py filtra la propria tabella dei
    # parametri di zteinfo3 con questa mappa (199 -> 14 parametri, 11 -> 3
    # richieste HTTP per ciclo di poll). None = comportamento upstream.
    param_overrides = None
    if MC888_PRUNE_ENABLED and router_type == ROUTER_TYPE_MC888:
        param_overrides = MC888_ZTEINFO3_GROUPS
    return mc.run_commands(
        str(ip),
        str(password),
        username,
        commands,
        phone_number=phone_number,
        message=message,
        param_overrides=param_overrides,
    )
