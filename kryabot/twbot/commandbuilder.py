from typing import List, Union

from twbot.command.CommandBase import CommandBase
import twbot.command.event as event
import twbot.command.general as general
import twbot.command.telegram as telegram
from twbot.object.MessageContext import MessageContext

command_list: List = event.export() + general.export() + telegram.export()


def build(command_name: str, context: MessageContext) -> Union[CommandBase, None]:
    cmd = next((cmd for cmd in command_list if str(command_name).lower() in cmd.names and list(set(context.rights).intersection(cmd.access))), None)
    if cmd is None:
        return None

    return cmd(context)
