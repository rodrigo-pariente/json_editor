"""Module for storing DataNavigator REPL possible actions."""

from collections.abc import Callable
import os
from pathlib import Path
from pprint import pprint
import sys
from typing import TYPE_CHECKING
from data_utils import smart_cast
from file_utils import read_file, save_file


if TYPE_CHECKING:
    from data_navigator import DataNavigator

commands = {}

def add_command(*commands_list: list[str]) -> Callable:
    """Decorator to add new commands automaticaly to commands dictionary."""
    def wrapper(func):
        for command in commands_list:
            commands[command] = func
        return func
    return wrapper

@add_command("append")
def append_data(dn: "DataNavigator", args) -> None:
    """Append data in current path without rewriting all data to maintain."""
    new_data = smart_cast(" ".join(args))
    cur_data = dn.get_data("current")

    match (new_data, cur_data):
        case (dict(), dict()):
            cur_data.update(new_data)

        case (list(), list()):
            cur_data.extend(new_data)

        case (a,b) if all(isinstance(d, (int, str, float)) for d in (a,b)):
            if isinstance(cur_data, str) or isinstance(new_data, str):
                cur_data = str(cur_data)
                new_data = str(new_data)
            dn.change_data(f"{cur_data + new_data}", "current")

        case _:
            print(f"Could not append {new_data}.")

@add_command("cast")
def cast_value(dn: "DataNavigator", args: list[str]) -> None:
    """Smart cast data in given path."""
    if len(args) != 1:
        print("Usage: cast <path>")
        return
    path = "current" if args[0] == "." else args[0]
    data = dn.get_data(path)
    dn.change_data(smart_cast(data), path, force_type=True)

@add_command("cls", "clear")
def clear_screen(*_) -> None:
    """Clean the screen without leaving the REPL"""
    os.system("cls" if os.name == "nt" else "clear")

@add_command("del-key")
def del_key(dn: "DataNavigator", indexes: list[str]) -> None:
    """Delete data based on given index."""
    cur_data = dn.get_data("current")
    for i in indexes:
        if isinstance(cur_data, (dict, list)):
            try:
                cur_data.pop(i)
            except (KeyError, IndexError):
                print("No value of index {i} in data.")
        else:
            print("Can only del-key from dictionary or list only.")

@add_command("del-val")
def del_val(dn: "DataNavigator", values: list[str]) -> None:
    """Delete value, key or item based on given value."""
    cur_data = dn.get_data("current")
    for i in values:
        if dn.literal:
            i = smart_cast(i)

        if i == ".":
            new_value = None

        if isinstance(cur_data, dict):
            new_value = {k: v for k, v in cur_data.items() if v != i}
        elif isinstance(cur_data, list):
            new_value = cur_data.remove(i)
        else:
            print(f"Could not delete {i}.")
            continue

        dn.change_data(new_value, "current", force_type=True)

@add_command("exit", "quit")
def exit_repl(*_) -> None:
    """Exit the script."""
    sys.exit(0)

@add_command("cd")
def move(dn: "DataNavigator", indexes: list[str] | str) -> None:
    """Move path based on given indexes."""
    def is_index(index: str, data: dict | list) -> bool:
        if isinstance(data, dict):
            return index in data
        if isinstance(data, list):
            return index.isdigit() and int(index) in range(len(data))
        return False

    for i in Path(*indexes).parts: # maybe its interior be another func
        if i == "..":
            if dn.path.as_posix() != ".":
                dn.path = dn.path.parent
            else:
                print("ERROR: You are at root level.")
        elif i == "\\":
            dn.path = Path(".")
        elif is_index(i, dn.get_data("current")):
            dn.path = dn.path.joinpath(i)
        else:
            print("ERROR: Cannot navigate into this type.")

    pprint(dn.get_data("current"))

@add_command("ls", "list")
def list_data(dn: "DataNavigator", *_) -> None:
    """Print data in current working data path."""
    pprint(dn.get_data("current"))

@add_command("print")
def print_public(dn: "DataNavigator", var_names: list[str]) -> None:
    """Show variable value based on it's name."""
    if not var_names:
        print("Available variables: ", ", ".join(dn.public.keys()))
        return

    for var in var_names:
        print(f"{var}: {dn.public.get(var, 'Variable not found')}")

@add_command("restart")
def restart(dn: "DataNavigator", *_) -> None:
    """Restart DataNavigator data to the original state."""
    dn.data = read_file(dn.filename)
    pprint(dn.get_data("current"))

@add_command("!")
def run_command(_, args) -> None:
    """Let you pass shell commands without leaving the application."""
    if args:
        os.system(" ".join(args))
    else:
        print("ERROR: No command given.")

@add_command("save")
def save(dn: "DataNavigator", *_) -> None:
    """Save DataNavigator modified data into filename."""
    save_file(dn.filename, dn.data)
    print(f"Saved at {dn.filename}.")

@add_command("flag")
def set_flag(dn: "DataNavigator", args: list[str, str]) -> None:
    """Set DataNavigator flag True or False."""
    two_args = len(args) == 2
    args_are_str = all(isinstance(arg, str) for arg in args)
    value_is_valid = args[1].lower() in ("on", "off")

    if two_args and args_are_str and value_is_valid:
        flag = args[0]
        value = bool(args[1].lower() == "on")
        dn.flag_setter(flag, value)
    else:
        print("usage: flag <flag> [bool value]")

@add_command("set")
def set_value(dn: "DataNavigator", new_value: list[str], show: bool = True) -> None:
    """Set new value in current path data."""
    dn.change_data(" ".join(new_value), "current")

    if show:
        pprint(dn.get_data("current"))

@add_command("+l")
def temporary_literal(dn: "DataNavigator", args: list[str]) -> None:
    """Quick execution of command with literal on."""
    if args:
        func = args[0]
        if func in commands:
            tmp_literal = dn.literal
            try:
                set_flag(dn, ["literal", "on"])
                commands[func](dn, args[1:])
            finally:
                dn.literal = tmp_literal
            return

    print("Usage: +l <command> [args]")

@add_command("uncast")
def uncast_value(dn: "DataNavigator", args: list[str]) -> None:
    """Cast data in given path as str."""
    if len(args) != 1:
        print("Usage: uncast <path>")
        return
    path = "current" if args[0] == "." else args[0]
    data = dn.get_data(path)
    dn.change_data(str(data), path, force_type=True)
