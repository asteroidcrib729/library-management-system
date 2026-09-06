"""PowerShell-inspired interactive application shell."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import DummyHistory, FileHistory
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from library_management import __version__
from library_management.cli.theme import PROMPT_STYLE, create_console
from library_management.config import Settings
from library_management.domain import (
    BookCopy,
    BookCopyStatus,
    DomainValidationError,
    FeedbackStatus,
    FineStatus,
    RequestStatus,
    UserRole,
)
from library_management.services import (
    AccountService,
    ApplicationError,
    AuthenticatedPrincipal,
    AuthenticationService,
    AuthorizationError,
    BackupInfo,
    BookRequestView,
    CatalogEntry,
    CatalogService,
    CirculationService,
    DatabaseHealth,
    EngagementService,
    FeedbackView,
    FinancialService,
    FineView,
    InsightsService,
    LoanView,
    MaintenanceService,
    OperationalReport,
    PopularBookView,
    RecommendationView,
    ReservationView,
)


class LibraryShell:
    """Interactive command dispatcher for the library application."""

    def __init__(
        self,
        settings: Settings,
        account_service: AccountService,
        authentication_service: AuthenticationService,
        catalog_service: CatalogService,
        circulation_service: CirculationService,
        financial_service: FinancialService,
        engagement_service: EngagementService,
        insights_service: InsightsService,
        maintenance_service: MaintenanceService,
        *,
        console: Console | None = None,
        color_enabled: bool = True,
    ) -> None:
        settings.prepare()
        self._settings = settings
        self._account_service = account_service
        self._authentication_service = authentication_service
        self._catalog_service = catalog_service
        self._circulation_service = circulation_service
        self._financial_service = financial_service
        self._engagement_service = engagement_service
        self._insights_service = insights_service
        self._maintenance_service = maintenance_service
        self._principal: AuthenticatedPrincipal | None = None
        self._console = console or create_console(color_enabled=color_enabled)
        self._commands: dict[str, Callable[[str], bool]] = {
            "about": self._show_about,
            "acquire-request": self._acquire_request,
            "assess-fine": self._assess_fine,
            "add-book": self._add_book,
            "add-copy": self._add_copy,
            "archive-feedback": self._archive_feedback,
            "backup": self._backup_database,
            "backups": self._show_backups,
            "book": self._show_book,
            "books": self._show_books,
            "bootstrap-admin": self._bootstrap_administrator,
            "cancel-reservation": self._cancel_reservation,
            "checkout": self._checkout,
            "clear": self._clear,
            "copies": self._show_copies,
            "copy-status": self._change_copy_status,
            "create-librarian": self._create_librarian,
            "deactivate-account": self._deactivate_own_account,
            "deactivate-user": self._deactivate_user,
            "dashboard": self._show_dashboard,
            "db-health": self._show_database_health,
            "exit": self._exit,
            "fine": self._show_fine,
            "fines": self._show_fines,
            "feedbacks": self._show_feedback,
            "help": self._show_help,
            "login": self._login,
            "loans": self._show_loans,
            "logout": self._logout,
            "pay-fine": self._pay_fine,
            "popular": self._show_popular,
            "quit": self._exit,
            "register": self._register_member,
            "recommend": self._show_recommendations,
            "renew": self._renew_loan,
            "request-book": self._request_book,
            "requests": self._show_book_requests,
            "reservations": self._show_reservations,
            "reserve": self._reserve_book,
            "restore-backup": self._restore_backup,
            "review-feedback": self._review_feedback,
            "review-request": self._review_request,
            "return-copy": self._return_copy,
            "status": self._show_status,
            "submit-feedback": self._submit_feedback,
            "update-book": self._update_book,
            "waive-fine": self._waive_fine,
            "whoami": self._who_am_i,
        }
        self._session: PromptSession[str] = PromptSession(
            history=FileHistory(str(settings.history_path)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=WordCompleter(sorted(self._commands), ignore_case=True),
            style=PROMPT_STYLE,
        )
        self._form_session: PromptSession[str] = PromptSession(
            history=DummyHistory(),
            style=PROMPT_STYLE,
        )

    def run(self) -> None:
        """Run commands until the user exits or input reaches EOF."""
        self._show_welcome()
        while True:
            try:
                command_line = self._session.prompt(self._prompt())
            except KeyboardInterrupt:
                self._console.print("[muted]Use 'exit' to close the application.[/muted]")
                continue
            except EOFError:
                self._console.print("\n[muted]Session closed.[/muted]")
                return

            if not self.execute(command_line):
                return

    def execute(self, command_line: str) -> bool:
        """Execute one command; return whether the shell should continue."""
        command, _, arguments = command_line.strip().partition(" ")
        if not command:
            return True

        handler = self._commands.get(command.casefold())
        if handler is None:
            self._console.print(
                f"[error]Unknown command:[/error] {command}. "
                "Run [command]help[/command] to list available commands."
            )
            return True
        try:
            return handler(arguments.strip())
        except (ApplicationError, DomainValidationError) as error:
            self._console.print(f"[error]{escape(str(error))}[/error]")
            return True

    @staticmethod
    def _prompt() -> FormattedText:
        return FormattedText(
            [
                ("class:app", "LMS "),
                ("class:shell", "PS "),
                ("class:path", str(Path.cwd())),
                ("class:symbol", "> "),
            ]
        )

    def _show_welcome(self) -> None:
        self._console.print(
            Panel.fit(
                "[heading]Library Management System[/heading]\n[muted]Python 3.14 revamp[/muted]",
                border_style="accent",
            )
        )
        self._console.print("Run [command]help[/command] to see the available commands.\n")

    def _show_help(self, arguments: str) -> bool:
        del arguments
        table = Table(title="Available commands", header_style="heading")
        table.add_column("Command", style="command")
        table.add_column("Description")
        table.add_row("about", "Show application and technology information.")
        table.add_row(
            "acquire-request <request-id> <book-id>",
            "Link an approved request to the catalog (staff only).",
        )
        table.add_row("assess-fine <username> <amount>", "Assess a manual fine (staff only).")
        table.add_row("add-book", "Create a catalog record (staff only).")
        table.add_row("add-copy <book-id> [barcode]", "Add physical inventory (staff only).")
        table.add_row("archive-feedback <id>", "Archive reviewed feedback (staff only).")
        table.add_row("backup", "Create a validated database backup (administrator only).")
        table.add_row("backups", "List managed database backups (administrator only).")
        table.add_row("book <id>", "Show one book and its availability.")
        table.add_row("books [query]", "List or search the catalog.")
        table.add_row("bootstrap-admin", "Create the first administrator account once.")
        table.add_row("cancel-reservation <id>", "Cancel an active reservation.")
        table.add_row("checkout <username> <barcode>", "Check out a copy (staff only).")
        table.add_row("clear", "Clear the terminal display.")
        table.add_row("copies <book-id>", "Show physical copies and their status.")
        table.add_row("copy-status <barcode> <status>", "Update inventory status (staff only).")
        table.add_row("create-librarian", "Create a librarian (administrator only).")
        table.add_row("deactivate-account", "Deactivate your signed-in account.")
        table.add_row(
            "deactivate-user [username]", "Deactivate another account (administrator only)."
        )
        table.add_row("dashboard", "Show operational metrics (staff only).")
        table.add_row("db-health", "Check database integrity and consistency (administrator only).")
        table.add_row("help", "Show this command list.")
        table.add_row("fine <id>", "Show fine and settlement details.")
        table.add_row("fines [username]", "Show fine history; staff may inspect another user.")
        table.add_row("feedbacks [status]", "Show feedback; staff see all submissions.")
        table.add_row("login / logout", "Begin or end an authenticated session.")
        table.add_row("loans [username]", "Show personal loans; staff may inspect another user.")
        table.add_row("pay-fine <id>", "Record full payment (staff only).")
        table.add_row("popular [limit]", "Show the most-circulated available books.")
        table.add_row("register", "Create a member account.")
        table.add_row("recommend [limit]", "Show personalized available-book suggestions.")
        table.add_row("renew <loan-id>", "Renew an eligible active loan.")
        table.add_row("request-book", "Submit a book acquisition request.")
        table.add_row("requests [status]", "Show requests; staff see all submissions.")
        table.add_row("reservations", "Show your reservation history and queue positions.")
        table.add_row("reserve <book-id>", "Join a book's reservation queue.")
        table.add_row(
            "restore-backup <filename>", "Restore a validated backup (administrator only)."
        )
        table.add_row("review-feedback <id>", "Mark new feedback reviewed (staff only).")
        table.add_row(
            "review-request <id> <approved|rejected>",
            "Review a pending book request (staff only).",
        )
        table.add_row("return-copy <barcode>", "Return a checked-out copy (staff only).")
        table.add_row("status", "Show the current development status.")
        table.add_row("submit-feedback", "Submit feedback.")
        table.add_row("update-book <id>", "Update catalog metadata (staff only).")
        table.add_row("waive-fine <id>", "Waive a fine (administrator only).")
        table.add_row("whoami", "Show the signed-in account.")
        table.add_row("exit / quit", "Close the application.")
        self._console.print(table)
        return True

    def _show_about(self, arguments: str) -> bool:
        del arguments
        self._console.print(f"[heading]Library Management System[/heading] v{__version__}")
        self._console.print("Python 3.14 · SQLite · Argon2id · Pyrefly · Pytest")
        return True

    def _show_status(self, arguments: str) -> bool:
        del arguments
        self._console.print(
            "[success]Account, catalog, circulation, financial, engagement, insights, and "
            "maintenance workflows ready.[/success]"
        )
        self._console.print(f"Database: [muted]{self._settings.database_path}[/muted]")
        session_status = (
            f"Signed in as {escape(self._principal.username)} ({self._principal.role.value})."
            if self._principal is not None
            else "No account is signed in."
        )
        self._console.print(session_status)
        return True

    def _show_books(self, arguments: str) -> bool:
        principal = self._require_principal()
        query = arguments.strip() or None
        entries = self._catalog_service.browse(principal.user_id, query)
        if not entries:
            self._console.print("[warning]No matching books found.[/warning]")
            return True
        self._print_catalog(entries)
        return True

    def _show_book(self, arguments: str) -> bool:
        principal = self._require_principal()
        book_id = self._parse_positive_integer(arguments, "Usage: book <id>")
        entry = self._catalog_service.get_book(principal.user_id, book_id)
        book = entry.book
        details = Table(show_header=False, box=None)
        details.add_column(style="heading")
        details.add_column()
        details.add_row("ID", str(book.id))
        details.add_row("Title", escape(book.title))
        details.add_row("Author", escape(book.author))
        details.add_row("Publication year", str(book.publication_year))
        details.add_row("ISBN", escape(book.isbn or "—"))
        details.add_row("Category", escape(book.category or "—"))
        details.add_row("Description", escape(book.description or "—"))
        details.add_row("Available copies", f"{entry.available_copies} / {entry.total_copies}")
        self._console.print(details)
        return True

    def _show_copies(self, arguments: str) -> bool:
        principal = self._require_principal()
        book_id = self._parse_positive_integer(arguments, "Usage: copies <book-id>")
        copies = self._catalog_service.list_copies(principal.user_id, book_id)
        if not copies:
            self._console.print("[warning]This book has no physical copies.[/warning]")
            return True
        self._print_copies(copies)
        return True

    def _add_book(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "add-book")
        principal = self._require_staff_principal()
        title = self._ask("Title")
        author = self._ask("Author")
        publication_year = self._parse_positive_integer(
            self._ask("Publication year"), "Publication year must be a positive number."
        )
        isbn = self._optional_value(self._ask("ISBN (optional)"))
        category = self._optional_value(self._ask("Category (optional)"))
        description = self._optional_value(self._ask("Description (optional)"))
        book = self._catalog_service.add_book(
            principal.user_id,
            title,
            author,
            publication_year,
            isbn=isbn,
            category=category,
            description=description,
        )
        self._console.print(f"[success]Book {book.id} added to the catalog.[/success]")
        return True

    def _update_book(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        book_id = self._parse_positive_integer(arguments, "Usage: update-book <id>")
        existing = self._catalog_service.get_book(principal.user_id, book_id).book
        title = self._ask("Title", default=existing.title)
        author = self._ask("Author", default=existing.author)
        publication_year = self._parse_positive_integer(
            self._ask("Publication year", default=str(existing.publication_year)),
            "Publication year must be a positive number.",
        )
        isbn = self._optional_value(
            self._ask("ISBN (type - to clear)", default=existing.isbn or "")
        )
        category = self._optional_value(
            self._ask("Category (type - to clear)", default=existing.category or "")
        )
        description = self._optional_value(
            self._ask("Description (type - to clear)", default=existing.description or "")
        )
        updated = self._catalog_service.update_book(
            principal.user_id,
            book_id,
            title,
            author,
            publication_year,
            isbn=isbn,
            category=category,
            description=description,
        )
        self._console.print(f"[success]Book {updated.id} updated.[/success]")
        return True

    def _add_copy(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split(maxsplit=1)
        if not parts:
            raise ApplicationError("Usage: add-copy <book-id> [barcode]")
        book_id = self._parse_positive_integer(parts[0], "Usage: add-copy <book-id> [barcode]")
        barcode = parts[1].strip() if len(parts) == 2 else self._ask("Barcode")
        copy = self._catalog_service.add_copy(principal.user_id, book_id, barcode)
        self._console.print(
            f"[success]Copy '{escape(copy.barcode)}' added to book {book_id}.[/success]"
        )
        return True

    def _change_copy_status(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 2:
            raise ApplicationError("Usage: copy-status <barcode> <status>")
        try:
            status = BookCopyStatus(parts[1].casefold().replace("-", "_"))
        except ValueError as error:
            allowed = ", ".join(
                status.value for status in BookCopyStatus if status is not BookCopyStatus.ON_LOAN
            )
            raise ApplicationError(f"Status must be one of: {allowed}.") from error
        copy = self._catalog_service.update_copy_status(principal.user_id, parts[0], status)
        self._console.print(
            f"[success]Copy '{escape(copy.barcode)}' is now {copy.status.value}.[/success]"
        )
        return True

    def _reserve_book(self, arguments: str) -> bool:
        principal = self._require_principal()
        book_id = self._parse_positive_integer(arguments, "Usage: reserve <book-id>")
        view = self._circulation_service.reserve(principal.user_id, book_id)
        self._console.print(
            f"[success]Reservation {view.reservation.id} created for "
            f"'{escape(view.book_title)}' at queue position {view.queue_position}.[/success]"
        )
        return True

    def _show_reservations(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "reservations")
        principal = self._require_principal()
        reservations = self._circulation_service.list_reservations(principal.user_id)
        if not reservations:
            self._console.print("[warning]No reservations found.[/warning]")
            return True
        self._print_reservations(reservations)
        return True

    def _cancel_reservation(self, arguments: str) -> bool:
        principal = self._require_principal()
        reservation_id = self._parse_positive_integer(arguments, "Usage: cancel-reservation <id>")
        view = self._circulation_service.cancel_reservation(principal.user_id, reservation_id)
        self._console.print(
            f"[success]Reservation {view.reservation.id} for "
            f"'{escape(view.book_title)}' cancelled.[/success]"
        )
        return True

    def _checkout(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 2:
            raise ApplicationError("Usage: checkout <username> <barcode>")
        view = self._circulation_service.checkout(principal.user_id, parts[0], parts[1])
        self._console.print(
            f"[success]Loan {view.loan.id}: '{escape(view.book.title)}' checked out to "
            f"{escape(view.borrower_username)} until "
            f"{self._format_datetime(view.loan.due_at)}.[/success]"
        )
        return True

    def _return_copy(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 1:
            raise ApplicationError("Usage: return-copy <barcode>")
        view = self._circulation_service.return_copy(principal.user_id, parts[0])
        overdue_note = " The loan was overdue." if view.is_overdue else ""
        fine_note = ""
        if view.assessed_fine is not None:
            fine_note = (
                f" Fine {view.assessed_fine.id} assessed: "
                f"{self._financial_service.currency_code} {view.assessed_fine.amount:.2f}."
            )
        self._console.print(
            f"[success]Copy '{escape(view.copy.barcode)}' returned from "
            f"{escape(view.borrower_username)}.{overdue_note}{fine_note}[/success]"
        )
        return True

    def _renew_loan(self, arguments: str) -> bool:
        principal = self._require_principal()
        loan_id = self._parse_positive_integer(arguments, "Usage: renew <loan-id>")
        view = self._circulation_service.renew(principal.user_id, loan_id)
        self._console.print(
            f"[success]Loan {view.loan.id} renewed until "
            f"{self._format_datetime(view.loan.due_at)} "
            f"({view.loan.renewal_count} renewal(s)).[/success]"
        )
        return True

    def _show_loans(self, arguments: str) -> bool:
        principal = self._require_principal()
        username = arguments.strip() or None
        loans = self._circulation_service.list_loans(principal.user_id, username)
        if not loans:
            self._console.print("[warning]No loans found.[/warning]")
            return True
        self._print_loans(loans)
        return True

    def _show_fines(self, arguments: str) -> bool:
        principal = self._require_principal()
        username = arguments.strip() or None
        views = self._financial_service.list_fines(principal.user_id, username)
        if not views:
            self._console.print("[warning]No fines found.[/warning]")
            return True
        self._print_fines(views)
        outstanding = sum(
            (view.fine.amount for view in views if view.fine.status is FineStatus.OUTSTANDING),
            start=Decimal("0.00"),
        )
        self._console.print(
            f"Outstanding total: [accent]{self._financial_service.currency_code} "
            f"{outstanding:.2f}[/accent]"
        )
        return True

    def _show_fine(self, arguments: str) -> bool:
        principal = self._require_principal()
        fine_id = self._parse_positive_integer(arguments, "Usage: fine <id>")
        view = self._financial_service.get_fine(principal.user_id, fine_id)
        self._print_fine_detail(view)
        return True

    def _assess_fine(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 2:
            raise ApplicationError("Usage: assess-fine <username> <amount>")
        amount = self._parse_money(parts[1])
        reason = self._ask("Reason")
        view = self._financial_service.assess_manual(principal.user_id, parts[0], amount, reason)
        self._console.print(
            f"[success]Fine {view.fine.id} assessed to {escape(view.username)}: "
            f"{self._financial_service.currency_code} {view.fine.amount:.2f}.[/success]"
        )
        return True

    def _pay_fine(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        fine_id = self._parse_positive_integer(arguments, "Usage: pay-fine <id>")
        note = self._optional_value(self._ask("Payment note (optional)"))
        view = self._financial_service.record_payment(principal.user_id, fine_id, note)
        self._console.print(
            f"[success]Fine {view.fine.id} paid in full: "
            f"{self._financial_service.currency_code} {view.fine.amount:.2f}.[/success]"
        )
        return True

    def _waive_fine(self, arguments: str) -> bool:
        principal = self._require_principal()
        fine_id = self._parse_positive_integer(arguments, "Usage: waive-fine <id>")
        reason = self._ask("Waiver reason")
        view = self._financial_service.waive(principal.user_id, fine_id, reason)
        self._console.print(
            f"[success]Fine {view.fine.id} waived: "
            f"{self._financial_service.currency_code} {view.fine.amount:.2f}.[/success]"
        )
        return True

    def _request_book(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "request-book")
        principal = self._require_principal()
        title = self._ask("Title")
        author = self._ask("Author")
        year_text = self._ask("Publication year (optional)")
        publication_year = (
            None
            if not year_text or year_text == "-"
            else self._parse_positive_integer(year_text, "Publication year must be positive.")
        )
        view = self._engagement_service.submit_book_request(
            principal.user_id, title, author, publication_year
        )
        self._console.print(
            f"[success]Book request {view.request.id} submitted for "
            f"'{escape(view.request.title)}'.[/success]"
        )
        return True

    def _show_book_requests(self, arguments: str) -> bool:
        principal = self._require_principal()
        status = self._parse_request_status(arguments)
        views = self._engagement_service.list_book_requests(principal.user_id, status)
        if not views:
            self._console.print("[warning]No book requests found.[/warning]")
            return True
        self._print_book_requests(views)
        return True

    def _review_request(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 2:
            raise ApplicationError("Usage: review-request <id> <approved|rejected>")
        request_id = self._parse_positive_integer(
            parts[0], "Usage: review-request <id> <approved|rejected>"
        )
        try:
            status = RequestStatus(parts[1].casefold())
        except ValueError as error:
            raise ApplicationError("Review decision must be approved or rejected.") from error
        note = self._optional_value(self._ask("Review note (required for rejection)"))
        view = self._engagement_service.review_book_request(
            principal.user_id, request_id, status, note
        )
        self._console.print(
            f"[success]Book request {view.request.id} marked {view.request.status.value}.[/success]"
        )
        return True

    def _acquire_request(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        parts = arguments.split()
        if len(parts) != 2:
            raise ApplicationError("Usage: acquire-request <request-id> <book-id>")
        request_id = self._parse_positive_integer(
            parts[0], "Usage: acquire-request <request-id> <book-id>"
        )
        book_id = self._parse_positive_integer(
            parts[1], "Usage: acquire-request <request-id> <book-id>"
        )
        view = self._engagement_service.mark_request_acquired(
            principal.user_id, request_id, book_id
        )
        self._console.print(
            f"[success]Book request {view.request.id} linked to "
            f"'{escape(view.acquired_book_title or '')}' and marked acquired.[/success]"
        )
        return True

    def _submit_feedback(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "submit-feedback")
        principal = self._require_principal()
        content = self._ask("Feedback")
        view = self._engagement_service.submit_feedback(principal.user_id, content)
        self._console.print(f"[success]Feedback {view.feedback.id} submitted.[/success]")
        return True

    def _show_feedback(self, arguments: str) -> bool:
        principal = self._require_principal()
        status = self._parse_feedback_status(arguments)
        views = self._engagement_service.list_feedback(principal.user_id, status)
        if not views:
            self._console.print("[warning]No feedback found.[/warning]")
            return True
        self._print_feedback(views)
        return True

    def _review_feedback(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        feedback_id = self._parse_positive_integer(arguments, "Usage: review-feedback <id>")
        view = self._engagement_service.review_feedback(principal.user_id, feedback_id)
        self._console.print(f"[success]Feedback {view.feedback.id} marked reviewed.[/success]")
        return True

    def _archive_feedback(self, arguments: str) -> bool:
        principal = self._require_staff_principal()
        feedback_id = self._parse_positive_integer(arguments, "Usage: archive-feedback <id>")
        view = self._engagement_service.archive_feedback(principal.user_id, feedback_id)
        self._console.print(f"[success]Feedback {view.feedback.id} marked archived.[/success]")
        return True

    def _register_member(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "register")
        principal = self._account_service.register_member(*self._collect_credentials())
        self._console.print(
            f"[success]Member account '{escape(principal.username)}' created.[/success]"
        )
        return True

    def _show_recommendations(self, arguments: str) -> bool:
        principal = self._require_principal()
        limit = self._parse_optional_result_limit(arguments, "recommend")
        views = self._insights_service.recommend(principal.user_id, limit)
        if not views:
            self._console.print("[warning]No available recommendations found.[/warning]")
            return True
        self._print_recommendations(views)
        return True

    def _show_popular(self, arguments: str) -> bool:
        principal = self._require_principal()
        limit = self._parse_optional_result_limit(arguments, "popular")
        views = self._insights_service.popular(principal.user_id, limit)
        if not views:
            self._console.print("[warning]No available books found.[/warning]")
            return True
        self._print_popular_books(views, title="Popular available books")
        return True

    def _show_dashboard(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "dashboard")
        principal = self._require_staff_principal()
        report = self._insights_service.operational_report(principal.user_id)
        self._print_dashboard(report)
        return True

    def _show_database_health(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "db-health")
        principal = self._require_administrator_principal()
        health = self._maintenance_service.health(principal.user_id)
        self._print_database_health(health)
        return True

    def _backup_database(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "backup")
        principal = self._require_administrator_principal()
        backup = self._maintenance_service.create_backup(principal.user_id)
        self._console.print(
            f"[success]Backup '{escape(backup.filename)}' created and validated "
            f"({self._format_bytes(backup.size_bytes)}).[/success]"
        )
        return True

    def _show_backups(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "backups")
        principal = self._require_administrator_principal()
        backups = self._maintenance_service.list_backups(principal.user_id)
        if not backups:
            self._console.print("[warning]No managed backups found.[/warning]")
            return True
        self._print_backups(backups)
        return True

    def _restore_backup(self, arguments: str) -> bool:
        principal = self._require_administrator_principal()
        parts = arguments.split()
        if len(parts) != 1:
            raise ApplicationError("Usage: restore-backup <filename>")
        confirmation = self._ask("Type RESTORE to replace the active database")
        if confirmation != "RESTORE":
            self._console.print("[warning]Database restoration cancelled.[/warning]")
            return True
        result = self._maintenance_service.restore_backup(principal.user_id, parts[0])
        self._console.print(
            f"[success]Restored '{escape(result.restored_backup.filename)}'. "
            f"Safety backup: '{escape(result.safety_backup.filename)}'.[/success]"
        )
        self._print_database_health(result.health)
        return True

    def _bootstrap_administrator(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "bootstrap-admin")
        principal = self._account_service.bootstrap_administrator(*self._collect_credentials())
        self._console.print(
            f"[success]Administrator '{escape(principal.username)}' created.[/success]"
        )
        return True

    def _create_librarian(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "create-librarian")
        actor = self._require_principal()
        principal = self._account_service.create_librarian(
            actor.user_id, *self._collect_credentials()
        )
        self._console.print(f"[success]Librarian '{escape(principal.username)}' created.[/success]")
        return True

    def _login(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "login")
        if self._principal is not None:
            raise AuthorizationError("Log out before signing in with another account.")
        username = self._ask("Username")
        password = self._ask("Password", secret=True)
        self._principal = self._authentication_service.authenticate(username, password)
        self._console.print(f"[success]Welcome, {escape(self._principal.display_name)}.[/success]")
        return True

    def _logout(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "logout")
        if self._principal is None:
            self._console.print("[muted]No account is signed in.[/muted]")
            return True
        username = self._principal.username
        self._principal = None
        self._console.print(f"[success]{escape(username)} signed out.[/success]")
        return True

    def _who_am_i(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "whoami")
        principal = self._require_principal()
        self._console.print(f"Name: [accent]{escape(principal.display_name)}[/accent]")
        self._console.print(f"Username: [command]{escape(principal.username)}[/command]")
        self._console.print(f"Role: {principal.role.value}")
        return True

    def _deactivate_own_account(self, arguments: str) -> bool:
        self._reject_arguments(arguments, "deactivate-account")
        principal = self._require_principal()
        confirmation = self._ask("Type DEACTIVATE to confirm")
        if confirmation != "DEACTIVATE":
            self._console.print("[warning]Account deactivation cancelled.[/warning]")
            return True
        self._account_service.deactivate_account(principal.user_id, principal.username)
        self._principal = None
        self._console.print("[success]Account deactivated and session closed.[/success]")
        return True

    def _deactivate_user(self, arguments: str) -> bool:
        principal = self._require_principal()
        target_username = arguments or self._ask("Username to deactivate")
        target = self._account_service.deactivate_account(principal.user_id, target_username)
        if target.user_id == principal.user_id:
            self._principal = None
        self._console.print(f"[success]Account '{escape(target.username)}' deactivated.[/success]")
        return True

    def _collect_credentials(self) -> tuple[str, str, str]:
        display_name = self._ask("Display name")
        username = self._ask("Username")
        password = self._ask("Password", secret=True)
        confirmation = self._ask("Confirm password", secret=True)
        if password != confirmation:
            raise ApplicationError("Passwords do not match.")
        return display_name, username, password

    def _ask(self, label: str, *, secret: bool = False, default: str = "") -> str:
        prompt = FormattedText([("class:app", label), ("class:symbol", ": ")])
        value = self._form_session.prompt(prompt, is_password=secret, default=default)
        return value if secret else value.strip()

    def _require_principal(self) -> AuthenticatedPrincipal:
        if self._principal is None:
            raise AuthorizationError("Sign in to use this command.")
        return self._principal

    def _require_staff_principal(self) -> AuthenticatedPrincipal:
        principal = self._require_principal()
        if principal.role not in {UserRole.LIBRARIAN, UserRole.ADMINISTRATOR}:
            raise AuthorizationError("Librarian or administrator permission is required.")
        return principal

    def _require_administrator_principal(self) -> AuthenticatedPrincipal:
        principal = self._require_principal()
        if principal.role is not UserRole.ADMINISTRATOR:
            raise AuthorizationError("Administrator permission is required.")
        return principal

    @staticmethod
    def _parse_positive_integer(value: str, error_message: str) -> int:
        try:
            parsed = int(value.strip())
        except ValueError as error:
            raise ApplicationError(error_message) from error
        if parsed <= 0:
            raise ApplicationError(error_message)
        return parsed

    @staticmethod
    def _parse_money(value: str) -> Decimal:
        try:
            amount = Decimal(value.strip())
        except InvalidOperation as error:
            raise ApplicationError(
                "Amount must be a positive number with at most two decimals."
            ) from error
        if not amount.is_finite() or amount <= 0 or amount.quantize(Decimal("0.01")) != amount:
            raise ApplicationError("Amount must be a positive number with at most two decimals.")
        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _parse_request_status(value: str) -> RequestStatus | None:
        if not value.strip():
            return None
        try:
            return RequestStatus(value.strip().casefold())
        except ValueError as error:
            allowed = ", ".join(status.value for status in RequestStatus)
            raise ApplicationError(f"Request status must be one of: {allowed}.") from error

    @staticmethod
    def _parse_feedback_status(value: str) -> FeedbackStatus | None:
        if not value.strip():
            return None
        try:
            return FeedbackStatus(value.strip().casefold())
        except ValueError as error:
            allowed = ", ".join(status.value for status in FeedbackStatus)
            raise ApplicationError(f"Feedback status must be one of: {allowed}.") from error

    @classmethod
    def _parse_optional_result_limit(cls, value: str, command: str) -> int | None:
        if not value.strip():
            return None
        return cls._parse_positive_integer(value, f"Usage: {command} [limit]")

    @staticmethod
    def _optional_value(value: str) -> str | None:
        cleaned = value.strip()
        return None if not cleaned or cleaned == "-" else cleaned

    def _print_catalog(self, entries: list[CatalogEntry]) -> None:
        table = Table(title="Library catalog", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Title", style="accent")
        table.add_column("Author")
        table.add_column("Year", justify="right")
        table.add_column("Available", justify="right")
        table.add_column("Total", justify="right")
        for entry in entries:
            table.add_row(
                str(entry.book.id),
                escape(entry.book.title),
                escape(entry.book.author),
                str(entry.book.publication_year),
                str(entry.available_copies),
                str(entry.total_copies),
            )
        self._console.print(table)

    def _print_copies(self, copies: list[BookCopy]) -> None:
        table = Table(title="Physical copies", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Barcode", style="command")
        table.add_column("Status")
        for copy in copies:
            table.add_row(str(copy.id), escape(copy.barcode), copy.status.value)
        self._console.print(table)

    def _print_reservations(self, views: list[ReservationView]) -> None:
        table = Table(title="Reservations", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Book", style="accent")
        table.add_column("Status")
        table.add_column("Queue", justify="right")
        table.add_column("Created")
        table.add_column("Resolved")
        for view in views:
            table.add_row(
                str(view.reservation.id),
                escape(view.book_title),
                view.reservation.status.value,
                str(view.queue_position) if view.queue_position is not None else "—",
                self._format_datetime(view.reservation.created_at),
                (
                    self._format_datetime(view.reservation.resolved_at)
                    if view.reservation.resolved_at is not None
                    else "—"
                ),
            )
        self._console.print(table)

    def _print_loans(self, views: list[LoanView]) -> None:
        table = Table(title="Loans", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Borrower")
        table.add_column("Book", style="accent")
        table.add_column("Barcode", style="command")
        table.add_column("Due")
        table.add_column("Returned")
        table.add_column("Renewals", justify="right")
        table.add_column("State")
        for view in views:
            state = (
                "returned"
                if view.loan.returned_at is not None
                else "overdue"
                if view.is_overdue
                else "active"
            )
            table.add_row(
                str(view.loan.id),
                escape(view.borrower_username),
                escape(view.book.title),
                escape(view.copy.barcode),
                self._format_datetime(view.loan.due_at),
                (
                    self._format_datetime(view.loan.returned_at)
                    if view.loan.returned_at is not None
                    else "—"
                ),
                str(view.loan.renewal_count),
                state,
            )
        self._console.print(table)

    def _print_fines(self, views: list[FineView]) -> None:
        table = Table(title="Fine history", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Account")
        table.add_column("Reason")
        table.add_column("Amount", justify="right")
        table.add_column("Status")
        table.add_column("Assessed")
        table.add_column("Settled")
        for view in views:
            table.add_row(
                str(view.fine.id),
                escape(view.username),
                escape(view.fine.reason),
                f"{self._financial_service.currency_code} {view.fine.amount:.2f}",
                view.fine.status.value,
                self._format_datetime(view.fine.assessed_at),
                (
                    self._format_datetime(view.fine.settled_at)
                    if view.fine.settled_at is not None
                    else "—"
                ),
            )
        self._console.print(table)

    def _print_fine_detail(self, view: FineView) -> None:
        details = Table(show_header=False, box=None)
        details.add_column(style="heading")
        details.add_column()
        details.add_row("Fine ID", str(view.fine.id))
        details.add_row("Account", escape(view.username))
        details.add_row("Loan ID", str(view.fine.loan_id) if view.fine.loan_id else "—")
        details.add_row("Reason", escape(view.fine.reason))
        details.add_row("Amount", f"{self._financial_service.currency_code} {view.fine.amount:.2f}")
        details.add_row("Status", view.fine.status.value)
        details.add_row("Assessed", self._format_datetime(view.fine.assessed_at))
        if view.settlement is not None:
            details.add_row("Settlement", view.settlement.kind.value)
            details.add_row("Recorded by", escape(view.settlement_actor_username or "—"))
            details.add_row("Recorded", self._format_datetime(view.settlement.created_at))
            details.add_row("Note", escape(view.settlement.note or "—"))
        self._console.print(details)

    def _print_book_requests(self, views: list[BookRequestView]) -> None:
        table = Table(title="Book requests", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Account")
        table.add_column("Title", style="accent")
        table.add_column("Author")
        table.add_column("Year", justify="right")
        table.add_column("Status")
        table.add_column("Reviewer")
        table.add_column("Catalog book")
        for view in views:
            table.add_row(
                str(view.request.id),
                escape(view.username),
                escape(view.request.title),
                escape(view.request.author),
                str(view.request.publication_year or "—"),
                view.request.status.value,
                escape(view.reviewer_username or "—"),
                escape(view.acquired_book_title or "—"),
            )
        self._console.print(table)

    def _print_feedback(self, views: list[FeedbackView]) -> None:
        table = Table(title="Feedback", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Account")
        table.add_column("Content", style="accent")
        table.add_column("Status")
        table.add_column("Submitted")
        table.add_column("Reviewer")
        for view in views:
            table.add_row(
                str(view.feedback.id),
                escape(view.username),
                escape(view.feedback.content),
                view.feedback.status.value,
                self._format_datetime(view.feedback.created_at),
                escape(view.reviewer_username or "—"),
            )
        self._console.print(table)

    def _print_recommendations(self, views: list[RecommendationView]) -> None:
        table = Table(title="Recommended available books", header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Title", style="accent")
        table.add_column("Author")
        table.add_column("Available", justify="right")
        table.add_column("Checkouts", justify="right")
        table.add_column("Why")
        for view in views:
            table.add_row(
                str(view.book.id),
                escape(view.book.title),
                escape(view.book.author),
                str(view.available_copies),
                str(view.historical_checkouts),
                escape(view.reason),
            )
        self._console.print(table)

    def _print_popular_books(self, views: list[PopularBookView], *, title: str) -> None:
        table = Table(title=title, header_style="heading")
        table.add_column("ID", justify="right")
        table.add_column("Title", style="accent")
        table.add_column("Author")
        table.add_column("Checkouts", justify="right")
        table.add_column("Available", justify="right")
        for view in views:
            table.add_row(
                str(view.book.id),
                escape(view.book.title),
                escape(view.book.author),
                str(view.historical_checkouts),
                str(view.available_copies),
            )
        self._console.print(table)

    def _print_dashboard(self, report: OperationalReport) -> None:
        metrics = Table(title="Operational dashboard", show_header=False)
        metrics.add_column(style="heading")
        metrics.add_column(justify="right")
        metrics.add_row("Generated", self._format_datetime(report.generated_at))
        metrics.add_row("Active accounts", str(report.active_users))
        metrics.add_row("Catalog titles", str(report.catalog_titles))
        metrics.add_row(
            "Available / total copies", f"{report.available_copies} / {report.total_copies}"
        )
        metrics.add_row("Active loans", str(report.active_loans))
        metrics.add_row("Overdue loans", str(report.overdue_loans))
        metrics.add_row("Active reservations", str(report.active_reservations))
        metrics.add_row(
            "Outstanding fines",
            f"{report.outstanding_fines} — {self._financial_service.currency_code} "
            f"{report.outstanding_fine_amount:.2f}",
        )
        metrics.add_row("Pending book requests", str(report.pending_requests))
        metrics.add_row("New feedback", str(report.new_feedback))
        self._console.print(metrics)
        if report.popular_books:
            self._print_popular_books(list(report.popular_books), title="Most circulated")

    def _print_database_health(self, health: DatabaseHealth) -> None:
        table = Table(title="Database health", show_header=False)
        table.add_column(style="heading")
        table.add_column()
        table.add_row("Overall", "healthy" if health.is_healthy else "unhealthy")
        table.add_row("Checked", self._format_datetime(health.checked_at))
        table.add_row("Database", escape(str(health.path)))
        table.add_row("Size", self._format_bytes(health.file_size_bytes))
        table.add_row(
            "Schema",
            f"{health.schema_version or 'unknown'} / expected {health.expected_version}",
        )
        table.add_row(
            "Integrity",
            ", ".join(escape(message) for message in health.integrity_messages) or "unavailable",
        )
        table.add_row("Foreign-key violations", str(health.foreign_key_violations))
        table.add_row("Circulation inconsistencies", str(health.circulation_inconsistencies))
        table.add_row("Financial inconsistencies", str(health.financial_inconsistencies))
        if health.inspection_error:
            table.add_row("Inspection error", escape(health.inspection_error))
        self._console.print(table)

    def _print_backups(self, backups: list[BackupInfo]) -> None:
        table = Table(title="Managed backups", header_style="heading")
        table.add_column("Filename", style="command")
        table.add_column("Created")
        table.add_column("Size", justify="right")
        table.add_column("Schema", justify="right")
        table.add_column("Healthy")
        table.add_column("Compatible")
        for backup in backups:
            table.add_row(
                escape(backup.filename),
                self._format_datetime(backup.created_at),
                self._format_bytes(backup.size_bytes),
                str(backup.health.schema_version or "—"),
                "yes" if backup.health.is_healthy else "no",
                "yes" if backup.health.is_compatible else "no",
            )
        self._console.print(table)

    @staticmethod
    def _format_bytes(size: int) -> str:
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if value < 1024 or unit == "GiB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        return value.astimezone().strftime("%Y-%m-%d %H:%M %Z")

    @staticmethod
    def _reject_arguments(arguments: str, command: str) -> None:
        if arguments:
            raise ApplicationError(f"Usage: {command}")

    def _clear(self, arguments: str) -> bool:
        del arguments
        self._console.clear()
        return True

    def _exit(self, arguments: str) -> bool:
        del arguments
        self._console.print("[muted]Session closed.[/muted]")
        return False
