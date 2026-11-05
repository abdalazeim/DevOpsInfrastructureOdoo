"""
Command Notebook UI - Terminal interface for the command notebook module.

Follows the existing TUI design patterns from menu_system.py and app.py.
"""
from __future__ import annotations

import os
from typing import Optional

from app.ui.command_notebook import (
    CommandNotebook,
    CATEGORIES,
    RISK_LEVELS,
    RISK_CLASSIFICATIONS,
    load_library,
    save_library,
)
from app.ui.command_notebook_generator import (
    OdooGeneratorConfig,
    generate_odoo_commands,
    generate_compose_yaml,
    validate_config,
    diff_text,
)

# ANSI color codes (match existing app.py style)
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


class CommandNotebookUI:
    """Terminal UI for the Command Notebook module."""

    def __init__(self, tui_instance):
        self.tui = tui_instance
        self.notebook = CommandNotebook()

    def run(self) -> None:
        """Main entry point for the Command Notebook."""
        while True:
            self._display_main_menu()
            choice = input(f"\n{BOLD}Select an option [1-9] or 0 to return: {RESET}").strip()
            if choice == "0":
                break
            elif choice == "1":
                self._browse_categories()
            elif choice == "2":
                self._view_all_commands()
            elif choice == "3":
                self._search_commands()
            elif choice == "4":
                self._odoo_docker_generator()
            elif choice == "5":
                self._add_command()
            elif choice == "6":
                self._edit_command()
            elif choice == "7":
                self._delete_command()
            elif choice == "8":
                self._export_import_menu()
            elif choice == "9":
                self._notebook_info()
            else:
                print(f"{RED}Invalid selection.{RESET}")
                input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Main menu display
    # ------------------------------------------------------------------
    def _display_main_menu(self) -> None:
        print(f"\n{CYAN}{BOLD}")
        print("=" * 70)
        print("  COMMAND NOTEBOOK")
        print("=" * 70)
        print(f"{RESET}")
        print(f"{DIM}A library of commands for viewing, editing, saving, searching, and copying.{RESET}")
        print(f"{DIM}Commands are NEVER executed from this module. Copy/review before use.{RESET}\n")
        print(f"  {BOLD}1.{RESET} Browse commands by category")
        print(f"  {BOLD}2.{RESET} View all commands")
        print(f"  {BOLD}3.{RESET} Search commands")
        print(f"  {BOLD}4.{RESET} Odoo Docker Installation Command Generator")
        print(f"  {BOLD}5.{RESET} Add new command")
        print(f"  {BOLD}6.{RESET} Edit existing command")
        print(f"  {BOLD}7.{RESET} Delete command")
        print(f"  {BOLD}8.{RESET} Export / Import library")
        print(f"  {BOLD}9.{RESET} Notebook information")
        print(f"\n  {BOLD}0.{RESET} Return to Main Menu")
        print(f"{CYAN}{'=' * 70}{RESET}")

    # ------------------------------------------------------------------
    # Browse by category
    # ------------------------------------------------------------------
    def _browse_categories(self) -> None:
        while True:
            print(f"\n{CYAN}{BOLD}COMMAND CATEGORIES{RESET}\n")
            cats = self.notebook.get_categories()
            for idx, cat in enumerate(cats, 1):
                print(f"  {BOLD}{idx}.{RESET} {cat['name']} ({cat['count']} commands)")
            print(f"\n  {BOLD}0.{RESET} Return to Command Notebook menu")
            choice = input(f"\n{BOLD}Select category [1-{len(cats)}] or 0 to return: {RESET}").strip()
            if choice == "0":
                break
            if not choice.isdigit() or not (1 <= int(choice) <= len(cats)):
                print(f"{RED}Invalid selection.{RESET}")
                continue
            cat = cats[int(choice) - 1]
            self._browse_category_commands(cat["key"], cat["name"])

    def _browse_category_commands(self, cat_key: str, cat_name: str) -> None:
        while True:
            commands = self.notebook.get_commands_by_category(cat_key)
            print(f"\n{CYAN}{BOLD}{cat_name.upper()}{RESET}")
            print(f"{DIM}{len(commands)} command(s){RESET}\n")
            if not commands:
                print(f"  {DIM}No commands in this category.{RESET}")
            else:
                for cmd in commands:
                    source_tag = " [builtin]" if cmd.get("source") == "builtin" else " [user]"
                    print(f"  {BOLD}{cmd['display_number']}.{RESET} {cmd['name']}{source_tag}")
                    print(f"     {DIM}{cmd.get('description', '')}{RESET}")
                    print(f"     {DIM}Risk: {cmd.get('risk_level', 'low')} | ID: {cmd['id']}{RESET}")
            print(f"\n  {BOLD}V.{RESET} View command details")
            print(f"  {BOLD}C.{RESET} Copy command text")
            print(f"  {BOLD}0.{RESET} Return to categories")
            choice = input(f"\n{BOLD}Select command number, V, C, or 0: {RESET}").strip().upper()
            if choice == "0":
                break
            elif choice == "V":
                self._view_command_by_number(commands)
            elif choice == "C":
                self._copy_command_by_number(commands)
            elif not commands:
                print(f"{YELLOW}No commands available.{RESET}")
            else:
                try:
                    num = int(choice)
                    if 1 <= num <= len(commands):
                        self._view_command_details(commands[num - 1])
                    else:
                        print(f"{RED}Invalid selection.{RESET}")
                except ValueError:
                    print(f"{RED}Invalid selection.{RESET}")

    def _view_command_by_number(self, commands: list) -> None:
        try:
            num = int(input(f"Enter command number [1-{len(commands)}]: ").strip())
            if 1 <= num <= len(commands):
                self._view_command_details(commands[num - 1])
            else:
                print(f"{RED}Invalid number.{RESET}")
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")

    def _copy_command_by_number(self, commands: list) -> None:
        try:
            num = int(input(f"Enter command number to copy [1-{len(commands)}]: ").strip())
            if 1 <= num <= len(commands):
                cmd = commands[num - 1]
                self._copy_command_text(cmd)
            else:
                print(f"{RED}Invalid number.{RESET}")
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")

    # ------------------------------------------------------------------
    # View all commands
    # ------------------------------------------------------------------
    def _view_all_commands(self) -> None:
        all_cmds = []
        for cat_key in CATEGORIES:
            cmds = self.notebook.get_commands_by_category(cat_key)
            for cmd in cmds:
                cmd["category_name"] = CATEGORIES.get(cmd.get("category", ""), cmd.get("category", ""))
                all_cmds.append(cmd)
        all_cmds.sort(key=lambda c: (c.get("category_name", ""), c["name"].lower()))
        print(f"\n{CYAN}{BOLD}ALL COMMANDS ({len(all_cmds)}){RESET}\n")
        if not all_cmds:
            print(f"  {DIM}No commands found.{RESET}")
        else:
            for idx, cmd in enumerate(all_cmds, 1):
                source_tag = " [builtin]" if cmd.get("source") == "builtin" else " [user]"
                print(f"  {BOLD}{idx}.{RESET} {cmd['name']}{source_tag}")
                print(f"     {DIM}Category: {cmd.get('category_name', '')} | Risk: {cmd.get('risk_level', 'low')}{RESET}")
                print(f"     {DIM}{cmd.get('description', '')}{RESET}")
        print(f"\n  {BOLD}V.{RESET} View command details")
        print(f"  {BOLD}C.{RESET} Copy command text")
        print(f"  {BOLD}0.{RESET} Return")
        choice = input(f"\n{BOLD}Select command number, V, C, or 0: {RESET}").strip().upper()
        if choice == "V":
            self._view_command_by_number(all_cmds)
        elif choice == "C":
            self._copy_command_by_number(all_cmds)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _search_commands(self) -> None:
        query = input(f"{BOLD}Enter search term (name, category, or command text): {RESET}").strip()
        if not query:
            print(f"{YELLOW}Search term cannot be empty.{RESET}")
            return
        results = self.notebook.search(query)
        print(f"\n{CYAN}{BOLD}SEARCH RESULTS FOR '{query}' ({len(results)}){RESET}\n")
        if not results:
            print(f"  {DIM}No matching commands found.{RESET}")
        else:
            for idx, cmd in enumerate(results, 1):
                source_tag = " [builtin]" if cmd.get("source") == "builtin" else " [user]"
                print(f"  {BOLD}{idx}.{RESET} {cmd['name']}{source_tag}")
                print(f"     {DIM}Category: {cmd.get('category_name', cmd.get('category', ''))} | Risk: {cmd.get('risk_level', 'low')}{RESET}")
                print(f"     {DIM}{cmd.get('description', '')}{RESET}")
        print(f"\n  {BOLD}V.{RESET} View command details")
        print(f"  {BOLD}C.{RESET} Copy command text")
        print(f"  {BOLD}0.{RESET} Return")
        choice = input(f"\n{BOLD}Select command number, V, C, or 0: {RESET}").strip().upper()
        if choice == "V":
            self._view_command_by_number(results)
        elif choice == "C":
            self._copy_command_by_number(results)

    # ------------------------------------------------------------------
    # Add command
    # ------------------------------------------------------------------
    def _add_command(self) -> None:
        print(f"\n{CYAN}{BOLD}ADD NEW COMMAND{RESET}\n")
        name = input("Command name: ").strip()
        if not name:
            print(f"{RED}Command name is required.{RESET}")
            return
        print("\nCategories:")
        cat_keys = list(CATEGORIES.keys())
        for idx, key in enumerate(cat_keys, 1):
            print(f"  {idx}. {CATEGORIES[key]}")
        try:
            cat_idx = int(input(f"\nSelect category [1-{len(cat_keys)}]: ").strip())
            if not (1 <= cat_idx <= len(cat_keys)):
                print(f"{RED}Invalid category.{RESET}")
                return
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")
            return
        category = cat_keys[cat_idx - 1]
        command = input("Command text (multiline, press Enter twice to finish):\n")
        lines = [command]
        while True:
            line = input()
            if line == "" and lines[-1] == "":
                lines.pop()
                break
            lines.append(line)
        command = "\n".join(lines)
        description = input("Description (optional): ").strip()
        print("\nRisk levels: 1=low, 2=medium, 3=high, 4=critical")
        risk_choice = input("Select risk level [1-4, default 1]: ").strip() or "1"
        try:
            risk_level = RISK_LEVELS[int(risk_choice) - 1]
        except (ValueError, IndexError):
            risk_level = "low"
        try:
            cmd_id = self.notebook.add_command(
                name=name,
                command=command,
                category=category,
                description=description,
                risk_level=risk_level,
            )
            print(f"\n{GREEN}Command added successfully (ID: {cmd_id}).{RESET}")
        except Exception as exc:
            print(f"{RED}Failed to add command: {exc}{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Edit command
    # ------------------------------------------------------------------
    def _edit_command(self) -> None:
        cmd_id = input("Enter command ID to edit: ").strip()
        if not cmd_id:
            print(f"{RED}Command ID is required.{RESET}")
            return
        cmd = self.notebook.get_command(cmd_id)
        if not cmd:
            print(f"{RED}Command not found: {cmd_id}{RESET}")
            return
        print(f"\n{CYAN}{BOLD}EDIT COMMAND: {cmd['name']}{RESET}\n")
        print(f"  Current name: {cmd['name']}")
        print(f"  Current category: {CATEGORIES.get(cmd.get('category', ''), cmd.get('category', ''))}")
        print(f"  Current risk: {cmd.get('risk_level', 'low')}")
        print(f"  Current description: {cmd.get('description', '')}")
        print(f"  Current command:\n{cmd.get('command', '')}\n")
        new_name = input(f"New name (leave blank to keep '{cmd['name']}'): ").strip() or cmd["name"]
        new_desc = input(f"New description (leave blank to keep): ").strip()
        if new_desc == "":
            new_desc = cmd.get("description", "")
        print("\nCategories:")
        cat_keys = list(CATEGORIES.keys())
        current_cat_idx = cat_keys.index(cmd.get("category", cat_keys[0])) + 1 if cmd.get("category") in cat_keys else 1
        for idx, key in enumerate(cat_keys, 1):
            marker = " (current)" if idx == current_cat_idx else ""
            print(f"  {idx}. {CATEGORIES[key]}{marker}")
        try:
            cat_idx_input = input(f"\nSelect category [1-{len(cat_keys)}, Enter to keep]: ").strip()
            new_category = cat_keys[int(cat_idx_input) - 1] if cat_idx_input else cmd.get("category", "ubuntu_system")
        except (ValueError, IndexError):
            new_category = cmd.get("category", "ubuntu_system")
        print("Current command text:")
        print("---")
        print(cmd.get("command", ""))
        print("---")
        new_command = input("\nNew command text (multiline, Enter twice to finish, blank to keep current):\n")
        if new_command == "":
            new_command = cmd.get("command", "")
        else:
            lines = [new_command]
            while True:
                line = input()
                if line == "" and lines[-1] == "":
                    lines.pop()
                    break
                lines.append(line)
            new_command = "\n".join(lines)
        print("\nRisk levels: 1=low, 2=medium, 3=high, 4=critical")
        risk_choice = input(f"Select risk level [1-4, current={cmd.get('risk_level', 'low')}]: ").strip()
        try:
            new_risk = RISK_LEVELS[int(risk_choice) - 1] if risk_choice else cmd.get("risk_level", "low")
        except (ValueError, IndexError):
            new_risk = cmd.get("risk_level", "low")
        try:
            self.notebook.update_command(
                cmd_id=cmd_id,
                name=new_name,
                command=new_command,
                category=new_category,
                description=new_desc,
                risk_level=new_risk,
            )
            print(f"\n{GREEN}Command updated successfully.{RESET}")
        except Exception as exc:
            print(f"{RED}Failed to update command: {exc}{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Delete command
    # ------------------------------------------------------------------
    def _delete_command(self) -> None:
        cmd_id = input("Enter command ID to delete: ").strip()
        if not cmd_id:
            print(f"{RED}Command ID is required.{RESET}")
            return
        cmd = self.notebook.get_command(cmd_id)
        if not cmd:
            print(f"{RED}Command not found: {cmd_id}{RESET}")
            return
        source_tag = " (built-in)" if cmd.get("source") == "builtin" else " (user)"
        print(f"\n{RED}{BOLD}DELETE COMMAND{RESET}")
        print(f"  Name: {cmd['name']}{source_tag}")
        print(f"  Category: {CATEGORIES.get(cmd.get('category', ''), cmd.get('category', ''))}")
        print(f"  Command: {cmd.get('command', '')[:80]}...")
        confirm = input(f"\n{RED}Are you sure you want to delete this command? [y/N]: {RESET}").strip().lower()
        if confirm == "y":
            try:
                self.notebook.delete_command(cmd_id)
                print(f"{GREEN}Command deleted successfully.{RESET}")
            except Exception as exc:
                print(f"{RED}Failed to delete command: {exc}{RESET}")
        else:
            print(f"{YELLOW}Delete cancelled.{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------
    def _export_import_menu(self) -> None:
        while True:
            print(f"\n{CYAN}{BOLD}EXPORT / IMPORT{RESET}\n")
            print(f"  {BOLD}1.{RESET} Export library to JSON file")
            print(f"  {BOLD}2.{RESET} Import library from JSON file")
            print(f"  {BOLD}0.{RESET} Return")
            choice = input(f"\n{BOLD}Select an option [1-2] or 0 to return: {RESET}").strip()
            if choice == "0":
                break
            elif choice == "1":
                self._export_library()
            elif choice == "2":
                self._import_library()
            else:
                print(f"{RED}Invalid selection.{RESET}")

    def _export_library(self) -> None:
        default_path = os.path.join(os.getcwd(), "command_notebook_export.json")
        path = input(f"Export file path [{default_path}]: ").strip() or default_path
        try:
            self.notebook.export_library(path)
            print(f"{GREEN}Library exported to: {path}{RESET}")
        except Exception as exc:
            print(f"{RED}Export failed: {exc}{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    def _import_library(self) -> None:
        path = input("Import file path: ").strip()
        if not path:
            print(f"{RED}File path is required.{RESET}")
            return
        if not os.path.exists(path):
            print(f"{RED}File not found: {path}{RESET}")
            return
        merge = input("Merge with existing library? [Y/n]: ").strip().lower() != "n"
        try:
            result = self.notebook.import_library(path, merge=merge)
            print(f"{GREEN}Import completed: {result['imported']} imported, {result['skipped']} skipped.{RESET}")
        except Exception as exc:
            print(f"{RED}Import failed: {exc}{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Notebook info
    # ------------------------------------------------------------------
    def _notebook_info(self) -> None:
        total = self.notebook.count()
        builtin = len(self.notebook.get_builtin_command_ids())
        user = len(self.notebook.get_user_command_ids())
        print(f"\n{CYAN}{BOLD}NOTEBOOK INFORMATION{RESET}\n")
        print(f"  Total commands: {total}")
        print(f"  Built-in commands: {builtin}")
        print(f"  User/imported commands: {user}")
        print(f"  Library file: data/command_notebook/library.json")
        print(f"  Categories: {len(CATEGORIES)}")
        print("\n  Categories:")
        for cat_key, cat_name in CATEGORIES.items():
            count = len(self.notebook.get_commands_by_category(cat_key))
            print(f"    - {cat_name}: {count} commands")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # View command details + copy
    # ------------------------------------------------------------------
    def _view_command_details(self, cmd: dict) -> None:
        source_tag = " [built-in]" if cmd.get("source") == "builtin" else " [user]"
        print(f"\n{CYAN}{BOLD}COMMAND DETAILS{RESET}")
        print(f"  Name: {cmd['name']}{source_tag}")
        print(f"  ID: {cmd['id']}")
        print(f"  Category: {CATEGORIES.get(cmd.get('category', ''), cmd.get('category', ''))}")
        print(f"  Risk level: {cmd.get('risk_level', 'low')}")
        print(f"  Description: {cmd.get('description', '')}")
        print(f"  Created: {cmd.get('created_at', '')}")
        print(f"  Modified: {cmd.get('modified_at', '')}")
        print(f"\n  Command text:")
        print(f"  {'-' * 60}")
        print(cmd.get("command", ""))
        print(f"  {'-' * 60}")
        print(f"\n  {BOLD}C.{RESET} Copy command text")
        print(f"  {BOLD}0.{RESET} Return")
        choice = input(f"\n{BOLD}Select C to copy, or 0 to return: {RESET}").strip().upper()
        if choice == "C":
            self._copy_command_text(cmd)

    def _copy_command_text(self, cmd: dict) -> None:
        """Display command text for manual copying (never executes)."""
        risk = str(cmd.get("risk_classification") or cmd.get("risk_level") or "SAFE").upper()
        if risk in ("HIGH", "DESTRUCTIVE"):
            color = RED if risk == "DESTRUCTIVE" else YELLOW
            print(f"\n{color}{BOLD}WARNING: {risk} RISK COMMAND{RESET}")
            print(f"{color}Review carefully before using. This notebook never executes commands.{RESET}")
            confirm = input(f"{BOLD}Type YES to show/copy this command text: {RESET}").strip()
            if confirm != "YES":
                print(f"{YELLOW}Copy cancelled.{RESET}")
                input(f"\n{DIM}Press Enter to continue...{RESET}")
                return
        print(f"\n{CYAN}{BOLD}COPY COMMAND TEXT{RESET}")
        print(f"{DIM}Copy the text below manually. This command is NOT executed.{RESET}\n")
        print(cmd.get("command", ""))
        print(f"\n{DIM}Command ID: {cmd.get('id', '')} | Name: {cmd.get('name', '')} | Risk: {risk}{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    # ------------------------------------------------------------------
    # Odoo Docker Installation Command Generator (read-only, no execution)
    # ------------------------------------------------------------------
    def _odoo_docker_generator(self) -> None:
        print(f"\n{CYAN}{BOLD}ODOO DOCKER INSTALLATION COMMAND GENERATOR{RESET}")
        print(f"{DIM}Generates editable/copyable commands from selected config. No commands are executed.{RESET}\n")

        profile = getattr(self.tui, "profile", None)
        seed_cfg = self._seed_generator_config_from_profile(profile)
        print(f"{DIM}Read-only config source: {'TUI profile' if profile else 'defaults'}{RESET}")
        print(f"{DIM}Defaults (Odoo {seed_cfg.odoo_version}): image={seed_cfg.odoo_image}, PG={seed_cfg.postgres_image}, "
              f"HTTP={seed_cfg.http_host_port}, LP={seed_cfg.longpolling_host_port}, dir={seed_cfg.deployment_dir}{RESET}\n")

        version = input(f"Odoo version [17/18/19, default {seed_cfg.odoo_version}]: ").strip() or seed_cfg.odoo_version
        if version not in {"17", "18", "19"}:
            print(f"{RED}Unsupported Odoo version: {version}{RESET}")
            input(f"\n{DIM}Press Enter to continue...{RESET}")
            return

        # Re-seed for selected version
        seed_cfg = self._seed_generator_config_from_profile(profile, odoo_version=version)
        cfg = OdooGeneratorConfig(
            odoo_version=version,
            odoo_image=input(f"Odoo image [{seed_cfg.odoo_image}]: ").strip() or seed_cfg.odoo_image,
            postgres_image=input(f"PostgreSQL image [{seed_cfg.postgres_image}]: ").strip() or seed_cfg.postgres_image,
            http_host_port=self._input_int(f"HTTP host port [{seed_cfg.http_host_port}]: ", seed_cfg.http_host_port),
            http_internal_port=self._input_int(f"HTTP internal port [{seed_cfg.http_internal_port}]: ", seed_cfg.http_internal_port),
            longpolling_host_port=self._input_int(f"Longpolling host port [{seed_cfg.longpolling_host_port}]: ", seed_cfg.longpolling_host_port),
            longpolling_internal_port=self._input_int(f"Longpolling internal port [{seed_cfg.longpolling_internal_port}]: ", seed_cfg.longpolling_internal_port),
            deployment_dir=input(f"Deployment directory [{seed_cfg.deployment_dir}]: ").strip() or seed_cfg.deployment_dir,
            compose_project_name=input(f"Docker Compose project name [{seed_cfg.compose_project_name}]: ").strip() or seed_cfg.compose_project_name,
            odoo_container_name=input(f"Odoo container name [{seed_cfg.odoo_container_name}]: ").strip() or seed_cfg.odoo_container_name,
            db_container_name=input(f"DB container name [{seed_cfg.db_container_name}]: ").strip() or seed_cfg.db_container_name,
            docker_network=input(f"Docker network [{seed_cfg.docker_network}]: ").strip() or seed_cfg.docker_network,
            restart_policy=input(f"Restart policy ({', '.join(['no','on-failure','on-failure:5','always','unless-stopped'])}) [{seed_cfg.restart_policy}]: ").strip() or seed_cfg.restart_policy,
            addons_dir=input(f"Addons directory (relative) [{seed_cfg.addons_dir}]: ").strip() or seed_cfg.addons_dir,
            config_dir=input(f"Config directory (relative) [{seed_cfg.config_dir}]: ").strip() or seed_cfg.config_dir,
            postgres_data_dir=input(f"PostgreSQL data directory (relative) [{seed_cfg.postgres_data_dir}]: ").strip() or seed_cfg.postgres_data_dir,
            deployment_mode=(input(f"Deployment mode [local/domain, default {seed_cfg.deployment_mode}]: ").strip() or seed_cfg.deployment_mode).lower(),
            domain=input(f"Domain (domain mode only) [{seed_cfg.domain}]: ").strip() or seed_cfg.domain,
        ).normalized()

        ok, errors, warnings = validate_config(cfg)
        if warnings:
            print(f"\n{YELLOW}{BOLD}Validation warnings:{RESET}")
            for w in warnings:
                print(f"  - {w}")
        if not ok:
            print(f"\n{RED}{BOLD}Configuration invalid; generation aborted:{RESET}")
            for e in errors:
                print(f"  - {e}")
            input(f"\n{DIM}Press Enter to continue...{RESET}")
            return

        ok, commands, errors, warnings, compose_text = generate_odoo_commands(cfg)
        if not ok:
            print(f"\n{RED}Generation failed:{RESET}")
            for e in errors:
                print(f"  - {e}")
            input(f"\n{DIM}Press Enter to continue...{RESET}")
            return

        print(f"\n{GREEN}Generated {len(commands)} command(s) for Odoo {cfg.odoo_version}.{RESET}")
        groups = {}
        for c in commands:
            groups.setdefault(c.get("group", "Commands"), 0)
            groups[c.get("group", "Commands")] += 1
        for g, n in groups.items():
            print(f"  - {g}: {n}")

        # Show diffs for existing generated commands (preserve user edits)
        diffs = self.notebook.list_generated_diffs(commands, cfg.to_metadata())
        if diffs:
            print(f"\n{YELLOW}{len(diffs)} generated command(s) differ from saved versions.{RESET}")
            show = input("Show diffs? [y/N]: ").strip().lower() == "y"
            if show:
                for d in diffs[:20]:
                    print(f"\n{BOLD}{d['name']}{RESET}\n{d['diff'] or '(no diff text)'}")

        save = input(f"\n{BOLD}Save generated commands to notebook? [Y/n]: {RESET}").strip().lower() != "n"
        if save:
            stats = self.notebook.upsert_generated_commands(commands, cfg.to_metadata(), overwrite_generated=True)
            print(f"{GREEN}Saved: added={stats['added']}, updated={stats['updated']}, kept user-modified={stats['kept_user_modified']}{RESET}")

        show_compose = input("Show generated Docker Compose (text only, no file write)? [Y/n]: ").strip().lower() != "n"
        if show_compose:
            print(f"\n{CYAN}{BOLD}GENERATED DOCKER COMPOSE (REFERENCE TEXT){RESET}")
            print(f"{DIM}Review and save manually if desired. Notebook does not overwrite files automatically.{RESET}\n")
            print(compose_text)

        save_compose = input("Save Compose reference as a notebook command in Docker Compose category? [y/N]: ").strip().lower() == "y"
        if save_compose:
            self.notebook.add_command(
                name=f"Odoo {cfg.odoo_version} generated docker-compose ({cfg.compose_project_name})",
                command=compose_text,
                category="docker_compose",
                description="Generated Compose reference (review, save to file, and validate with `docker compose config` before use). No secrets embedded.",
                risk_level="safe",
                risk_classification="SAFE",
                source="generated",
                odoo_version=cfg.odoo_version,
                required_parameters=[f"PROJECT={cfg.compose_project_name}", f"FILE=docker-compose.odoo{cfg.odoo_version}.yml"],
                group="Dynamic Docker Compose Generator",
                generated_config=cfg.to_metadata(),
                generator="odoo_docker_installation",
                generated_key=f"compose_{cfg.odoo_version}_{cfg.compose_project_name}",
            )
            print(f"{GREEN}Compose reference saved to notebook (Docker Compose category).{RESET}")

        print(f"\n{DIM}Traefik note: this project uses Traefik (not Nginx). Domain/TLS routing should be configured in the infrastructure stack only when required and verified.{RESET}")
        input(f"\n{DIM}Press Enter to continue...{RESET}")

    @staticmethod
    def _input_int(prompt: str, default: int) -> int:
        raw = input(prompt).strip()
        if not raw:
            return int(default)
        try:
            return int(raw)
        except ValueError:
            return int(default)

    def _seed_generator_config_from_profile(self, profile, odoo_version: Optional[str] = None) -> OdooGeneratorConfig:
        """Read-only mapping from TUI profile/config; never mutates profile or executes anything."""
        return OdooGeneratorConfig.from_profile(profile, odoo_version=odoo_version)
