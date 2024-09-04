#!/usr/bin/env python3

import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

PREFIX = "TEMPLATE_VAR_"


@dataclass
class Var:
    key: str
    description: str

    lower_case: bool = False
    valid_python_name: bool = False
    no_prompt: bool = False
    regex: str | None = None

    transform: Callable[[str], str] | None = None


VARS = [
    Var(
        "project_name",
        "pip/package name of the project",
        lower_case=True,
        valid_python_name=True,
    ),
    Var("short_description", "Small one-line description of the project"),
    Var(
        "author",
        "Appears in pip and license. Format 'Your Name <Your Email>'"
        "(e.g 'John Doe <john@doe.net>')",
    ),
    Var(
        "github",
        "<owner|org>/<repo>",
        regex=r"^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_]+$",
    ),
    Var("gh_user", "Your github username"),
    Var(
        "year",
        "",
        no_prompt=True,
        transform=lambda _: str(datetime.datetime.now().year),
    ),
    # TODO add support for other licenses
    Var(
        "license",
        "License of the project",
        no_prompt=True,
        transform=lambda _: "MIT",
    ),
]

FILES = [
    "src",
    "docs",
    "LICENSE",
    "pyproject.toml",
    "README_template.md",
]

MOVE = {
    "README_template.md": "README.md",
}

CACHE_FILE_PATH = Path("/tmp/app_template_cache.json")


def move_file_and_delete_empty_parent(old: Path, new: Path):
    new.parent.mkdir(parents=True, exist_ok=True)
    old.rename(new)

    for p in old.parents:
        if not list(p.glob("*")):
            p.rmdir()


def main(cache: bool = True, dry_run: bool = False):
    console = Console()
    replacements = {}

    if cache and CACHE_FILE_PATH.exists():
        replacements = json.loads(CACHE_FILE_PATH.read_text())
        console.print("[yellow]Warning: using cached values:[/yellow]", replacements)

    for var in VARS:
        key = f"{PREFIX}{var.key}"
        value = ""
        if key in replacements:
            continue

        while True:
            if not var.no_prompt:
                value = Prompt.ask(f"[green]{var.description}[/green]", console=console)

            if var.transform:
                value = var.transform(value)

            if var.lower_case:
                value_post = value.lower()
                if value_post != value:
                    console.print(
                        "[yellow]Warning: converting to lower case: [/yellow]"
                        f"{value} -> {value_post}"
                    )
                value = value_post

            if var.valid_python_name:
                value_post = value.replace("-", "_")
                if value_post != value:
                    console.print(
                        "[yellow]Warning: converting to python name: [/yellow]"
                        f"{value} -> {value_post}"
                    )
                value = value_post

            if var.regex:
                if not re.match(var.regex, value):
                    console.print(f"[red]Invalid value:[/red] [yellow]{value}[/yellow]")
                    continue

            replacements[key] = value
            CACHE_FILE_PATH.write_text(json.dumps(replacements))
            break

    # show 'replacements' and ask for confirmation
    table = Table(title="Project variables")
    table.add_column("Variable", justify="left", style="cyan", no_wrap=True)
    table.add_column("Value", justify="center", style="magenta", no_wrap=False)
    for key in replacements:
        table.add_row(
            str(key).replace("TEMPLATE_VAR_", "").replace("_", " "), replacements[key]
        )
    console.print(table)
    if not Confirm.ask(
        "Do you want to continue with these settings?", default=True, console=console
    ):
        if CACHE_FILE_PATH.exists():
            CACHE_FILE_PATH.unlink()
        return

    # Get files --------------------------------------------------
    root = Path(__file__).parent.parent
    files: list[Path] = []
    for path_name in FILES:
        path = root.joinpath(path_name)
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            files.append(path)

    # Replace vars --------------------------------------------------
    for f in files:
        text = f.read_text()
        out_path = f.relative_to(root)

        # Replace in text
        for k, v in replacements.items():
            if k in text:
                console.print(f"Replacing  in {f}: |{k}| -> |{v}|")
                text = text.replace(k, v)
            if k in str(out_path):
                out_path = Path(str(out_path).replace(k, v))

        out_path = root / out_path

        # Replace in path
        if out_path != f:
            console.print(
                f"Renaming {f.relative_to(root)} -> {out_path.relative_to(root)}"
            )
            if not dry_run:
                move_file_and_delete_empty_parent(f, out_path)

        if not dry_run:
            out_path.write_text(text)

    # Remove template files ----------------------------------------
    if not dry_run:
        for k, v in MOVE.items():
            if (root / k).exists():
                (root / k).rename(root / v)


if __name__ == "__main__":
    typer.run(main)
