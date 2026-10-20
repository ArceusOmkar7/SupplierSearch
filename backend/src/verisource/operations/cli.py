"""Local operator entry points; python -m verisource.operations.cli --help."""

import argparse
import getpass
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from verisource.config import Settings, disable_external_tracing
from verisource.db.session import create_database_engine
from verisource.operations.preflight import preflight, setup_local
from verisource.security.sessions import change_buyer_password, provision_buyer


def main() -> int:
    disable_external_tracing()
    parser = argparse.ArgumentParser(
        description="VeriSource local operations; no seed-data commands"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup-local")
    setup.add_argument("--data-dir", type=Path)
    commands.add_parser("create-buyer")
    commands.add_parser("change-buyer-password")
    capture = commands.add_parser("capture-source", help="capture a genuine source with provenance")
    capture.add_argument("url")
    capture.add_argument("--name", required=True)
    capture.add_argument(
        "--kind", required=True, choices=["supplier", "official", "issuer", "buyer_request"]
    )
    capture.add_argument("--publisher", required=True)
    capture.add_argument("--rights", required=True)
    capture.add_argument("--attribution", required=True)
    capture.add_argument("--coverage", required=True, nargs="+")
    capture.add_argument("--publication-cutoff")
    importer = commands.add_parser("import-source", help="import one captured official export")
    importer.add_argument("manifest", type=Path)
    importer.add_argument("--kind", choices=["auto", "tabular", "bis-qco"], default="auto")
    evaluate = commands.add_parser(
        "evaluate", help="evaluate actual independent audit labels and observed timings"
    )
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--profile", choices=["local-free"], default="local-free")
    evaluate.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("preflight")
    check.add_argument("--profile", choices=["local-free"], default="local-free")
    args = parser.parse_args()
    settings = Settings()
    try:
        if args.command == "setup-local":
            if args.data_dir is not None and args.data_dir.resolve() != settings.data_root:
                raise ValueError("Set VERISOURCE_DATA_ROOT to the requested directory first")
            setup_local(settings)
            print(
                "Local database, checkpoint schema, private files and deletion ledger initialized."
            )
            return 0
        if args.command == "create-buyer":
            username = input("Username: ")
            display_name = input("Display name: ")
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords did not match")
            engine = create_database_engine(settings)
            try:
                with Session(engine) as db, db.begin():
                    provision_buyer(db, username, password, display_name)
            finally:
                engine.dispose()
            print("Local buyer account created.")
            return 0
        if args.command == "change-buyer-password":
            username = input("Username: ")
            current_password = getpass.getpass("Current password: ")
            new_password = getpass.getpass("New password (at least 12 characters): ")
            if new_password != getpass.getpass("Confirm new password: "):
                raise ValueError("Passwords did not match")
            engine = create_database_engine(settings)
            try:
                with Session(engine) as db, db.begin():
                    change_buyer_password(db, username, current_password, new_password)
            finally:
                engine.dispose()
            print("Password changed. Existing login sessions revoked.")
            return 0
        if args.command == "capture-source":
            from verisource.operations.capture import CaptureRefused, capture_source

            try:
                path = capture_source(
                    args.url,
                    name=args.name,
                    kind=args.kind,
                    publisher=args.publisher,
                    rights=args.rights,
                    attribution=args.attribution,
                    coverage=args.coverage,
                    publication_cutoff=args.publication_cutoff,
                )
            except CaptureRefused as exc:
                print(f"Capture refused: {exc}. Nothing was written or substituted.")
                return 1
            print(f"Captured {path.name} with its provenance manifest.")
            return 0
        if args.command == "import-source":
            from verisource.operations.imports import run_import

            print(json.dumps(run_import(settings, args.manifest, kind=args.kind), indent=2))
            return 0
        if args.command == "evaluate":
            from verisource.operations.evaluation import evaluate as run_evaluation
            from verisource.operations.evaluation import write_result

            engine = create_database_engine(settings)
            try:
                outcome = run_evaluation(args.manifest, engine)
            finally:
                engine.dispose()
            target = write_result(outcome, args.output)
            for item in outcome["results"]:
                print(f"{item['criterion']}: {item['status']}")
                for reason in item["unmet"]:
                    print(f"  unmet: {reason}")
            print(f"Result written to {target}")
            return 0 if all(item["status"] == "passed" for item in outcome["results"]) else 2
        result = preflight(settings)
        print(json.dumps(result, indent=2))
        return 0 if result["ready"] else 1
    except ValueError as exc:
        print(str(exc))
        return 1
    except SQLAlchemyError:
        print("Local database operation failed. Check availability or choose a unique username.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
