import sys
import traceback
from ..config import load_config, copy_user_config
from ..kernel import setup_kernel_state
from .. import var
from ..xorg import configure_xorg, cleanup_xorg_conf, do_xsetup, set_DPI
from ..hacks.gdm import kill_gdm_server
from ..logging import logging


def setup_pre_daemon_start():

    daemon_run_id = var.make_daemon_run_id()
    var.write_daemon_run_id(daemon_run_id)

    with logging("daemon", daemon_run_id):

        try:
            print("# Daemon pre-start hook")

            cleanup_xorg_conf()
            copy_user_config()
            var.remove_last_acpi_call_state()
            startup_mode = var.get_startup_mode()

            print("Startup mode is: %s" % startup_mode)

            state = {
                "type": "pending_pre_xorg_start",
                "requested_mode": startup_mode,
                "current_mode": None
            }

            var.write_state(state)

        except Exception as e:

            print("Daemon startup error")
            print(traceback.format_exc())

            state = {
                "type": "startup_failed",
                "startup_mode": startup_mode,
                "daemon_run_id": daemon_run_id
            }

            var.write_state(state)
            sys.exit(1)

        else:
            print("Daemon pre-start hook completed successfully. Calling Xorg pre-start hook.")

    setup_pre_xorg_start()


def setup_pre_xorg_start():

    prev_state = var.load_state()

    if prev_state is None or prev_state["type"] != "pending_pre_xorg_start":
        return

    switch_id = var.make_switch_id()

    with logging("switch", switch_id):

        try:
            print("# Xorg pre-start hook")

            requested_mode = prev_state["requested_mode"]

            print("Requested mode is: %s" % requested_mode)

            kill_gdm_server()
            config = load_config()
            setup_kernel_state(config, prev_state, requested_mode)
            configure_xorg(config, requested_mode)

            state = {
                "type": "pending_post_xorg_start",
                "switch_id": switch_id,
                "requested_mode": requested_mode,
            }

            var.write_state(state)

        except Exception as e:

            print("Xorg pre-start setup error")
            print(traceback.format_exc())

            cleanup_xorg_conf()

            state = {
                "type": "pre_xorg_start_failed",
                "switch_id": switch_id,
                "requested_mode": requested_mode
            }

            var.write_state(state)
            sys.exit(1)

        else:
            print("Xorg pre-start hook completed successfully.")


def setup_post_xorg_start():

    prev_state = var.load_state()

    if prev_state is None or prev_state["type"] != "pending_post_xorg_start":
        return

    switch_id = prev_state["switch_id"]

    with logging("switch", switch_id):

        try:
            print("# Xorg post-start hook")

            requested_mode = prev_state["requested_mode"]

            do_xsetup(requested_mode)
            config = load_config()
            set_DPI(config)

            state = {
                "type": "done",
                "switch_id": switch_id,
                "current_mode": requested_mode
            }

            var.write_state(state)

        except Exception as e:

            print("Xorg post-start setup error")
            print(traceback.format_exc())

            state = {
                "type": "post_xorg_start_failed",
                "switch_id": switch_id,
                "requested_mode": requested_mode
            }

            var.write_state(state)
            sys.exit(1)

        else:
            print("Xorg post-start hook completed successfully.")
