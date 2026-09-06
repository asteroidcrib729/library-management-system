"""Application entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from functools import partial

from library_management import __version__
from library_management.cli import LibraryShell
from library_management.config import Settings
from library_management.database import Database
from library_management.repositories.sqlite import SqliteUnitOfWork
from library_management.security import PasswordService
from library_management.services import (
    AccountService,
    AuthenticationService,
    CatalogService,
    CirculationService,
    EngagementService,
    FinancialService,
    FinePolicy,
    InsightsService,
    MaintenanceService,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the Library Management System CLI.")
    parser.add_argument(
        "--version",
        action="version",
        version=f"Library Management System {__version__}",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable colored output",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    settings = Settings.from_environment()
    settings.prepare()
    database = Database(settings.database_path)
    database.initialize()
    unit_of_work_factory = partial(SqliteUnitOfWork, database)
    password_service = PasswordService()
    account_service = AccountService(unit_of_work_factory, password_service)
    authentication_service = AuthenticationService(unit_of_work_factory, password_service)
    catalog_service = CatalogService(unit_of_work_factory)
    fine_policy = FinePolicy()
    circulation_service = CirculationService(unit_of_work_factory, fine_policy=fine_policy)
    financial_service = FinancialService(unit_of_work_factory, policy=fine_policy)
    engagement_service = EngagementService(unit_of_work_factory)
    insights_service = InsightsService(unit_of_work_factory)
    maintenance_service = MaintenanceService(
        unit_of_work_factory, database, settings.backup_directory
    )
    shell = LibraryShell(
        settings,
        account_service,
        authentication_service,
        catalog_service,
        circulation_service,
        financial_service,
        engagement_service,
        insights_service,
        maintenance_service,
        color_enabled=not args.no_color,
    )
    shell.run()
