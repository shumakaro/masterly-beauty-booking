"""Create a PostgreSQL custom-format backup, or restore into a NEW isolated test database."""

import argparse
import os
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.compose")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--restore-test", action="store_true")
    args = parser.parse_args()
    command = ["docker", "compose", "--env-file", args.env_file]
    # COMPOSE_FILE may select the HTTPS override, but db is identical in both variants.
    if args.restore_test:
        target = "masterly_restore_test"
        # createdb fails if the database already exists. Never replace an existing database.
        with args.file.open("rb") as source:
            subprocess.run(
                command
                + [
                    "exec",
                    "-T",
                    "db",
                    "createdb",
                    "-U",
                    "postgres",
                    "-O",
                    "masterly",
                    target,
                ],
                check=True,
            )
            subprocess.run(
                command
                + [
                    "exec",
                    "-T",
                    "db",
                    "pg_restore",
                    "-U",
                    "postgres",
                    "--role=masterly",
                    "-d",
                    target,
                    "--exit-on-error",
                    "--single-transaction",
                    "--no-owner",
                    "--no-acl",
                ],
                stdin=source,
                check=True,
            )
        print(
            "Restored into NEW masterly_restore_test; the application database was not changed."
        )
    else:
        descriptor = os.open(args.file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as destination:
                subprocess.run(
                    command
                    + [
                        "exec",
                        "-T",
                        "db",
                        "pg_dump",
                        "-U",
                        "masterly",
                        "-d",
                        "masterly",
                        "--format=custom",
                        "--no-owner",
                        "--no-acl",
                    ],
                    stdout=destination,
                    check=True,
                )
        except BaseException:
            args.file.unlink(missing_ok=True)
            raise
        print(
            f"Backup created: {args.file}. Store an encrypted copy outside this server."
        )


if __name__ == "__main__":
    main()
