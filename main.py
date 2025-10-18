# SPDX-License-Identifier: MIT

"""Main entry point of the application."""

import argparse
import os
import sys

from fastlib import ConfigManager, LogConfig
from fastlib.constants import CONFIG_FILE, ENV

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_arguments() -> argparse.Namespace:
    """Parse and return command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fast web server with custom configurations"
    )

    parser.add_argument(
        "-e",
        "--env",
        type=str,
        choices=["dev", "test", "prod"],  # Add expected environments
        default="dev",
        help="Specify the runtime environment (dev|test|prod)",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        type=str,
        default=None,
        help="Path to a custom configuration file",
    )

    return parser.parse_args()


def setup_config(args: argparse.Namespace) -> None:
    """Set up configuration based on command line arguments."""
    os.environ[ENV] = args.env
    if args.config_file:
        os.environ[CONFIG_FILE] = args.config_file

    ConfigManager.register_custom_configs(LogConfig)
    ConfigManager.initialize_global_config()


def run_server() -> None:
    """Run the server."""
    from src.main.app.server import run

    run()


def main() -> None:
    """Main application entry point."""
    setup_config(parse_arguments())
    run_server()


if __name__ == "__main__":
    main()
