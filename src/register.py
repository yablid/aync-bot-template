# src/register.py
"""Script to manually register, edit, delete slash commands
$ python register.py list --type guild --guild_id 1234567890"""

import json
import logging
import os
import requests
import sys
import argparse
from dotenv import load_dotenv
from cfg.cfg import CFG
from typing import Literal

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_ID = os.getenv('APP_ID')
GUILD_IDS = [
    os.getenv('GUILD_ID'),
]
API = CFG['apis']['discord']
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}"}

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMANDS_DIR = os.path.join(ROOT_DIR, 'commands')

log = logging.getLogger(__name__)


def list_commands(cmd_type: Literal['guild', 'global'] = 'guild', guild_id: str = None) -> dict:
    """check existing guild or global commands for an app"""
    if cmd_type == 'guild' and not guild_id:
        guild_id = input("Please enter the guild ID: ")

    g = f"/guilds/{guild_id}/commands" if cmd_type == 'guild' else f"/commands"
    endpoint = API + f"/applications/{APP_ID}" + g

    r = requests.get(endpoint, headers=HEADERS)
    r.raise_for_status()
    data = json.loads(r.text)
    log.info(f"received data: {data}")
    cmd_list = {command['name']: command['id'] for command in data}

    print(f"command list: {cmd_list}")
    return cmd_list


def delete_commands(json_filename: str, cmd_type: Literal['guild', 'global'] = 'guild', guild_id: str = None) -> None:
    """delete (de-register) commands for an app"""
    if cmd_type == 'guild' and not guild_id:
        guild_id = input("Please enter the guild ID: ")

    g = f"/guilds/{guild_id}/commands" if cmd_type == 'guild' else f"/commands"
    endpoint = API + f"/applications/{APP_ID}" + g

    cmd_list = list_commands(cmd_type, guild_id)

    json_path = os.path.join(COMMANDS_DIR, json_filename + '.json')
    with open(json_path, 'r') as f:
        cmd_json = json.load(f)

    try:
        cmd_id = cmd_list[cmd_json['name']]
    except KeyError as e:
        raise Exception(f"'name' in: {json_path} doesn't match any registered commands. {e}")

    endpoint += "/" + cmd_id

    r = requests.delete(endpoint, headers=HEADERS)

    if r.status_code != 204:
        log.error(f"Error. {r.status_code} should be 204 No Content.")
    else:
        log.info(f"Returned {r.status_code}. Successfully deleted.")
        log.info(f"Current commands: {list_commands('guild', guild_id)}")

    return


def create_guild_command(json_filename: str, guild_id: str) -> None:
    """registers a guild command"""
    endpoints = [API + f"/applications/{APP_ID}" + f"/guilds/{guild_id}/commands"]

    json_path = os.path.join(COMMANDS_DIR, json_filename + '.json')
    with open(json_path, 'r') as f:
        cmd_json = json.load(f)

    log.info(f"Attempting to register command from json: {json_path}")

    for endpoint in endpoints:
        r = requests.post(endpoint, headers=HEADERS, json=cmd_json)

        if r.status_code == 201:
            log.info(f"Successfully created. Current commands: {list_commands('guild', guild_id)}")
        elif r.status_code == 200:
            log.info(f"Successfully edited.")
        else:
            raise Exception(f"Expected status code 201 (create) or 200 (edit). Received {r.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Script to manually register, edit, delete slash commands")
    subparsers = parser.add_subparsers(dest='command')

    # List commands
    list_parser = subparsers.add_parser('list', help='List existing commands')
    list_parser.add_argument('--type', choices=['guild', 'global'], default='guild', help='Type of commands to check')
    list_parser.add_argument('--guild_id', type=str, help='Guild ID (for guild commands)')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a command')
    delete_parser.add_argument('json_filename', type=str, help='Filename of JSON file with command payload')
    delete_parser.add_argument('--type', choices=['guild', 'global'], default='guild', help='Type of command to delete')
    delete_parser.add_argument('--guild_id', type=str, help='Guild ID (for guild commands)')

    # Create command
    create_parser = subparsers.add_parser('create_guild_command', help='Create a guild command')
    create_parser.add_argument('json_filename', type=str, help='Filename of JSON file with command payload')
    create_parser.add_argument('--guild_id', type=str, required=True, help='Guild ID')

    args = parser.parse_args()

    log.addHandler(logging.StreamHandler(sys.stdout))
    log.setLevel(logging.DEBUG)

    if args.command == 'list':
        list_commands(cmd_type=args.type, guild_id=args.guild_id)
    elif args.command == 'delete':
        delete_commands(args.json_filename, cmd_type=args.type, guild_id=args.guild_id)
    elif args.command == 'create_guild_command':
        create_guild_command(args.json_filename, args.guild_id)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
