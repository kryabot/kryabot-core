from typing import List, Union

from twbot.command.CommandBase import CommandBase
from twbot.command.event import *
from twbot.command.general import *
from twbot.command.telegram import *
from twbot.object.MessageContext import MessageContext

command_list: List = []
command_list.append(CancelEvent)
command_list.append(FinishRate)
command_list.append(StartEvent)
command_list.append(FinishEvent)
command_list.append(StartRate)
command_list.append(StartSubonlyEvent)
command_list.append(StartSubgiftEvent)
command_list.append(Spam)
command_list.append(MassBan)
command_list.append(UnlinkTelegram)
command_list.append(TelegramInvite)
command_list.append(MassTimeout)


def build(command_name: str, context: MessageContext)->Union[CommandBase, None]:
    for cmd in command_list:
        if str(command_name).lower() in cmd.names:
            print('Found matching command by name {}'.format(command_name))
            if list(set(context.rights).intersection(cmd.access)):
                print('Access to command {} is granted!'.format(command_name))
                return cmd(context)
            else:
                print('No access to command {}'.format(command_name))
                continue

    return None
    #cmd = next((cmd for cmd in command_list if str(command_name).lower() in cmd.names and list(set(context.rights).intersection(cmd.access))), None)
    # if cmd is None:
    #     print('Failed to find command {}, user rights: {}'.format(command_name, context.rights))
    #     return None
    #
    # return cmd(context)
