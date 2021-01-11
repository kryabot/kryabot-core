import asyncio

from tgbot.commands.UserAccess import UserAccess
from tgbot.commands.stringparser import StringParser

from tgbot.commands.help import *
from tgbot.commands.getter import *
from tgbot.commands.actions import *
from tgbot.commands.reminder import *
from tgbot.commands.award import *
from tgbot.commands.vote import *
from tgbot.commands.moderation import *
from tgbot.commands.manage import *
from tgbot.commands.items import *

helper_bot_name = '@KryaHelpBot'
command_list = []
# Any
command_list.append(Whoami)
command_list.append(Invite)
# Verified
command_list.append(KryaHelp)
command_list.append(KbSet)
command_list.append(KbGet)
command_list.append(KbDel)
command_list.append(KbGetAll)
command_list.append(MyWarns)
command_list.append(SetMyVk)
command_list.append(SetMyUt)
command_list.append(SetMyInst)
command_list.append(Inventory)
# Chat admin
command_list.append(Whois)
command_list.append(Banmedia)
command_list.append(AddBan)
command_list.append(AddVip)
command_list.append(Unlist)
command_list.append(Next)
command_list.append(ShowNonVerifiedList)
command_list.append(AwardHelp)
command_list.append(ReminderHelp)
command_list.append(DelReminder)
command_list.append(CompleteReminder)
command_list.append(AddReminder)
command_list.append(GetReminders)
command_list.append(DeleteAward)
command_list.append(SetAward)
command_list.append(GetAwards)
command_list.append(BanWord)
command_list.append(AddWarn)
command_list.append(GetWarns)
command_list.append(SettingHelp)
command_list.append(OnStream)
command_list.append(SetWelcomeMessage)
command_list.append(SubHistory)
command_list.append(Award)
command_list.append(AddHelper)
command_list.append(EnableGlobalEvents)
command_list.append(DisableGlobalEvents)
command_list.append(ChatInventory)
# Chat super admin
command_list.append(SetReminderCooldown)
command_list.append(StartMasskick)
command_list.append(ChatModeSub)
command_list.append(ChatModeFollow)
command_list.append(ChatModeAny)
command_list.append(SetMaxWarns)
command_list.append(SetWarnMute)
command_list.append(SetWarnExpire)
command_list.append(ChatEntranceEnable)
command_list.append(ChatEntranceDisable)
command_list.append(SetKickDays)
command_list.append(SetMinSubMonths)
command_list.append(SetLang)
command_list.append(ShowReport)
command_list.append(HideReport)
# Chat owner
command_list.append(AddSudo)
command_list.append(UnSudo)
# Supporter
# TODO groups instead of levels
# Super admin
command_list.append(UserReport)
command_list.append(MassMessage)
command_list.append(ReloadTranslations)
command_list.append(GlobalUserReport)
command_list.append(SpeedTest)
command_list.append(DLCoub)
command_list.append(SpawnBoss)
command_list.append(SpawnBox)
command_list.append(SpawnLove)
command_list.append(SpawnSnowing)


async def build(command_name, event, parsed):
    if helper_bot_name.lower() in command_name:
        command_name = command_name.replace(helper_bot_name.lower(), '')

    cmd = next((cmd for cmd in command_list if command_name in cmd.command_names), None)
    if cmd is None:
        return None

    return cmd(event=event, parsed=parsed)


async def process_command(event):
    without_prefix = event.raw_text[len('/')::].lstrip(' ')

    parsed = StringParser().process_string(without_prefix)

    try:
        command_name = parsed.pop(0)
    except:
        return

    command = await build(command_name.lower(), event, parsed)
    if command is None:
        return

    await command.process()


async def run(event):
    try:
        await process_command(event)
    except Exception as err:
        await event.client.exception_reporter(err, event.raw_text)


async def update_command_list(client):
    await client.send_message('@BotFather', '/setcommands')
    await asyncio.sleep(2)
    await client.send_message('@BotFather', helper_bot_name)
    await asyncio.sleep(2)

    text = ''
    for command in command_list:
        if command.access_level == UserAccess.SUPER_ADMIN:
            continue

        text += '{} - {}\n'.format(command.command_names[0], str(command.access_level).replace('UserAccess.', ''))

    await client.send_message('@BotFather', text)