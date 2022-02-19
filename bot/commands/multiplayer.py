import asyncio
from typing import List, TYPE_CHECKING

from blob import Context
from bot.bot import CrystalBot
from helpers import new_utils
from objects.Channel import Channel
from objects.Multiplayer import Match
from objects.constants import Privileges
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from objects.constants.multiplayer import (
    MultiSpecialModes,
    MatchScoringTypes,
    MatchTeamTypes,
)
from packets.Builder.index import PacketBuilder
from objects.BanchoObjects import Message

if TYPE_CHECKING:
    from objects.Player import Player


def user_in_channel(player: "Player", msg: "Message") -> bool:
    if not msg.to.startswith("#"):
        return False

    channel = Context.channels.get(msg.to)
    if not channel:
        return False

    if player in channel.users:
        return True

    return False


def can_take_match(
    player: "Player",
    match: Match,
    check_tourney_host: bool = False,
    check_referee: bool = True,
):
    if (
        player.privileges & Privileges.USER_TOURNAMENT_STAFF
    ) == Privileges.USER_TOURNAMENT_STAFF:
        return True  # check if user has tournament staff privileges

    if check_tourney_host:
        # Check condition when player is have tourney in host match
        if match.is_tourney and match.host_tourney == player:
            return True

    if match.host == player:
        return True  # user has created this match/user has host in non-tourney game

    if check_referee:
        if player.id in match.referees:
            return True

    return False


async def mp_make(args: List[str], player: "Player", _):
    if len(args) < 2:
        return "Enter in format: !mp make <name>"

    match_name = " ".join(args[1:]).strip()
    if player.match:
        return "First of all, you need to close the previous match"

    match = Match(
        match_id=Context.matches_id,
        name=match_name,
        password=new_utils.random_hash(),
        is_tourney=True,
        host=player,
        host_tourney=player,
    )
    Context.matches_id += 1  # increment match id
    match.beatmap_id = 0

    # Create match temp channel
    match_channel = Channel(
        server_name=f"#multi_{match.id}",
        description=f"Channel for #multi_{match.id}",
        public_read=True,
        public_write=True,
        temp_channel=True,
    )

    # Register that channel and match
    Context.channels[f"#multi_{match.id}"] = match_channel
    match.channel = match_channel
    Context.matches[match.id] = match

    # TODO: IRC Ignore join
    if not player.is_tourneymode:
        await match.join_player(player, match.password)  # allow player to join match
    else:
        # join only in channel
        await match_channel.join_channel(player)

    info_packet = await PacketBuilder.NewMatch(match)
    for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
        if not user.is_in_lobby:
            continue
        user.enqueue(info_packet)

    if player.is_tourneymode:
        player.id_tourney = match.id
    return f"Tourney match #{match.id} created!"


async def mp_join(args: List[str], player: "Player", _):
    if len(args) < 2 or not args[1].isdigit():
        return "Enter in format: !mp join <id>"

    match_id = int(args[1])
    if match_id not in Context.matches:
        return "Match not found"

    match = Context.matches[match_id]
    if not can_take_match(player, match, True):
        return "You cant join this match!"

    if not player.is_tourneymode:
        await match.join_player(player, match.password)  # allow player to join match
        return f"Attempting to join match #{match.id}"

    # join only in channel
    await match.channel.join_channel(player)
    player.id_tourney = match.id
    return f"Attempting to join match #{match.id} with tournament client!"


async def mp_close(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    await player.match.disband_match()
    if player.is_tourneymode:
        player.id_tourney = -1

    return "Match successfully disbanded"


async def mp_lock(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    player.match.is_locked = True
    return "This match has been locked"


async def mp_unlock(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    player.match.is_locked = False
    return "This match has been unlocked"


async def mp_size(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 2 or int(args[1]) > 16:
        return "Wrong syntax: !mp size <slots(2-16)>"

    match_size = int(args[1])
    await player.match.force_size(match_size)
    await player.match.update_match()
    return f"Match size changed to {match_size}"


async def mp_move(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 3 or not args[2].isdigit() or int(args[2]) < 0 or int(args[2]) > 16:
        return "Wrong syntax: !mp move <username> <slot>"

    username = args[1]
    new_slot_id = int(args[2])

    from_token = Context.players.get_token(name=username.lower())
    if not from_token:
        return "Player not found"

    res = await player.match.change_slot(from_token, new_slot_id)
    if res:
        result = f"Player {username} moved to slot {new_slot_id}"
    else:
        result = (
            "You can't use that slot: it's either already occupied by someone else or locked"
        )
    return result


async def mp_host(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp host <username>"

    username = args[1].strip()
    if not username:
        return "Please provide a username"

    to_token = Context.players.get_token(name=username.lower())
    res = await player.match.move_host(new_host=to_token)
    return f"{username} is now the host" if res else f"Couldn't give host to {username}"


async def mp_clear_host(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if not player.match.is_tourney:
        return "You cant remove host in not tourney game"

    await player.match.removeTourneyHost()
    return "Host has been removed from this match"


async def mp_start(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    async def _start():
        success = await player.match.start()
        if not success:
            await CrystalBot.ez_message(
                player.match.channel.server_name,
                "Couldn't start match. Make sure there are enough players and "
                "teams are valid. The match has been unlocked.",
            )
        else:
            await CrystalBot.ez_message(player.match.channel.server_name, "Have fun!")

    async def _decreaseTimer(t: int):
        while t > 0:
            if t % 10 == 0 or t <= 5:
                await CrystalBot.ez_message(
                    player.match.channel.server_name,
                    f"Match starts in {t} seconds.",
                )
            t -= 1
            await asyncio.sleep(1)

        await _start()

    startTime = 0
    if len(args) > 1 and args[1].isdigit():
        startTime = int(args[1])

    force = False if len(args) < 2 else args[1].lower() == "force"

    # Force everyone to ready
    someoneNotReady = False
    for slot in player.match.slots:
        if slot.status != SlotStatus.Ready and slot.token:
            someoneNotReady = True
            if force:
                slot.toggle_ready()

    if someoneNotReady and not force:
        return (
            "Some users aren't ready yet. Use '!mp start force' if you want to start the match, "
            "even with non-ready players."
        )

    if startTime == 0:
        await _start()
        return "Starting match"

    player.match.is_locked = True
    asyncio.ensure_future(_decreaseTimer(startTime))
    return (
        f"Match starts in {startTime} seconds. The match has been locked. "
        "Please don't leave the match during the countdown "
        "or you might receive a penalty."
    )


async def mp_abort(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    await player.match.abort()
    return "Match aborted!"


async def mp_invite(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match, check_tourney_host=True):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp invite <username>"

    username = args[1].strip()
    if not username:
        return "Please provide a username"

    to_token = Context.players.get_token(name=args[1].strip().lower())
    if not to_token:
        return "Player not found/not online"

    if to_token.is_bot:
        return "Sorry, you cant invite bots("

    msg = Message(
        sender=player.name,
        to=to_token.name,
        body=f"Come join to my game: [osump://{player.match.id}/{player.match.password if player.match.password else ''} {player.match.name}]",
        client_id=player.id,
    )
    await player.send_message(msg)
    return f"An invite to this match has been sent to {to_token.name}"


async def mp_map(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match, check_tourney_host=True):
        return "You cant do anything with that match"

    if (len(args) < 2 or not args[1].isdigit()) or (len(args) == 3 and not args[2].isdigit()):
        return "Wrong syntax: !mp map <beatmapid> [<gamemode>]"

    beatmapID = int(args[1])
    gameMode = int(args[2]) if len(args) == 3 else 0
    if gameMode < 0 or gameMode > 3:
        return "Gamemode must be 0, 1, 2 or 3"

    beatmapData = await Context.mysql.fetch(
        "SELECT * FROM beatmaps WHERE beatmap_id = %s LIMIT 1", [beatmapID]
    )
    if not beatmapData:
        return (
            "The beatmap you've selected couldn't be found in the database."
            "If the beatmap id is valid, please load the scoreboard first in "
            "order to cache it, then try again."
        )

    player.match.beatmap_id = beatmapID
    player.match.beatmap_name = beatmapData["song_name"]
    player.match.beatmap_md5 = beatmapData["beatmap_md5"]
    player.selected_game_mode = GameModes(gameMode)
    await player.match.unready_everyone()
    await player.match.update_match()
    return "Match map has been updated"


async def mp_set(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    # pylint: disable=too-many-boolean-expressions
    if (
        len(args) < 2
        or not args[1].isdigit()
        or (len(args) >= 3 and not args[2].isdigit())
        or (len(args) >= 4 and not args[3].isdigit())
    ):
        return "Wrong syntax: !mp set <teammode> [<scoremode>] [<size>]"

    match_team_type = MatchTeamTypes(int(args[1]))
    match_scoring_type = MatchScoringTypes(
        int(args[2]) if len(args) >= 3 else player.match.match_scoring_type.value
    )
    if not 0 <= match_team_type <= 3:
        return "Match team type must be between 0 and 3"

    if not 0 <= match_scoring_type <= 3:
        return "Match scoring type must be between 0 and 3"

    if player.match.match_team_type != MatchTeamTypes(match_team_type):
        if (
            MatchTeamTypes(match_team_type) == MatchTeamTypes.TagTeamVs
            or match_team_type == MatchTeamTypes.TeamVs
        ):
            for (i, slot) in enumerate(player.match.slots):
                if slot.team == SlotTeams.Neutral:
                    slot.team = SlotTeams.Red if i % 2 == 1 else SlotTeams.Blue
        else:
            for slot in player.match.slots:
                slot.team = SlotTeams.Neutral

    player.match.match_team_type = match_team_type
    player.match.match_scoring_type = match_scoring_type
    if len(args) >= 4:
        await player.match.force_size(int(args[3]))

    await player.match.change_special_mods(player.match.match_freemod)
    await player.match.update_match()
    return "Match settings have been updated!"


async def mp_timer(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 1:
        return "Wrong argument"

    secondsWatch = int(args[1])

    if player.match.timer_runned:
        await CrystalBot.ez_message(
            player.match.channel.server_name,
            "You can't run another timer, if you had another runned timer.\n"
            "Enter !mp aborttimer to stop.",
        )
        return False

    async def _decreaseTimer(t):
        while t > 0 and not player.match.timer_force:
            if t % 10 == 0 or t <= 5:
                await CrystalBot.ez_message(
                    player.match.channel.server_name,
                    f"Timer ends in {t} seconds.",
                )
            t -= 1

            await asyncio.sleep(1)

        await CrystalBot.ez_message(player.match.channel.server_name, "Time is up!")
        player.match.timer_force = False
        player.match.timer_runned = False

    player.match.timer_runned = True
    asyncio.ensure_future(_decreaseTimer(secondsWatch - 1))
    return "Timer started!"


async def mp_abort_timer(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if not player.match.timer_runned:
        return "Timer is not runned!"

    if player.match.timer_force:
        return "Another dude stopped timer!"

    player.match.timer_force = True
    return False


async def mp_kick(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp kick <username>"

    to_token = Context.players.get_token(name=args[1].strip().lower())
    if not to_token:
        return "Player not found/not online"

    if to_token not in player.match.channel.users:
        return "User not in lobby"

    for slot in player.match.slots:
        if slot.token == to_token:
            slot.lock_slot()
            slot.unlock_slot()
            break

    await player.match.update_match()
    return f"{to_token.name} has been kicked from the match"


async def mp_password(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    password = "" if len(args) < 2 or not args[1].strip() else args[1]
    player.match.password = password
    await player.match.update_match()
    return "Match password has been changed!"


async def mp_random_password(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    password = new_utils.random_hash()
    player.match.password = password
    await player.match.update_match()
    return "Match password has been changed to a random one"


async def mp_mods(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match, check_tourney_host=True):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp mods <mod1> [<mod2>] ..."

    new_mods = Mods(0)
    freeMod = False
    for _mod in args[1:]:
        if _mod.lower().strip() == "hd":
            new_mods |= Mods.Hidden
        elif _mod.lower().strip() == "hr":
            new_mods |= Mods.HardRock
        elif _mod.lower().strip() == "dt":
            new_mods |= Mods.DoubleTime
        elif _mod.lower().strip() == "fl":
            new_mods |= Mods.Flashlight
        elif _mod.lower().strip() == "fi":
            new_mods |= Mods.FadeIn
        elif _mod.lower().strip() == "nf":
            new_mods |= Mods.NoFail
        elif _mod.lower().strip() == "ez":
            new_mods |= Mods.Easy
        if _mod.lower().strip() == "none" or _mod.lower().strip() == "nomod":
            new_mods = Mods(0)

        if _mod.lower().strip() == "freemod":
            freeMod = True

    await player.match.change_special_mods(MultiSpecialModes(int(freeMod)))
    await player.match.change_mods(new_mods, player)
    await player.match.unready_everyone()
    await player.match.update_match()
    return "Match mods have been updated!"


async def mp_team(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 3:
        return "Wrong syntax: !mp team <username> <color(red/blue)>"

    to_token = Context.players.get_token(name=args[1].strip().lower())
    if not to_token:
        return "Player not found/not online"

    if to_token not in player.match.channel.users:
        return "User not in lobby"

    color = args[2].lower().strip()
    if color not in ["red", "blue"]:
        return "Team colour must be red or blue"

    for slot in player.match.slots:
        if slot.token == to_token:
            slot.team = SlotTeams.Blue if color == "blue" else SlotTeams.Red
            break
    await player.match.update_match()
    return f"{to_token.name} is now in {color} team"


async def mpScoreV(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    if len(args) < 2 or args[1] not in ("1", "2"):
        return "Wrong syntax: !mp scorev <1|2>"

    player.match.match_scoring_type = (
        MatchScoringTypes.ScoreV2 if args[1] == "2" else MatchScoringTypes.Score
    )
    await player.match.update_match()
    return f"Match scoring type set to score v{args[1]}"


async def mp_settings(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    link = "no match history"
    if player.match.vinse_id:
        link = f"[https://kurikku.pw/matches/{player.match.vinse_id} match history]"

    msg = f"{link}\nPLAYERS IN THIS MATCH:\n"
    empty = True
    for slot in player.match.slots:
        if not slot.token:
            continue

        readable_statuses = {
            SlotStatus.Ready: "ready",
            SlotStatus.NotReady: "not ready",
            SlotStatus.NoMap: "no map",
            SlotStatus.Playing: "playing",
        }

        if slot.status not in readable_statuses:
            readable_status = "???"
        else:
            readable_status = readable_statuses[slot.status]
        empty = False
        # pylint: disable=consider-using-f-string
        msg += "* [{team}] <{status}> ~ {username}{mods}\n".format(
            team="red"
            if slot.team == SlotTeams.Red
            else "blue"
            if slot.team == SlotTeams.Blue
            else "!! no team !!",
            status=readable_status,
            username=slot.token.name,
            mods=" (+ {})".format(new_utils.readable_mods(slot.mods)) if slot.mods > 0 else "",
        )

    if empty:
        msg += "Nobody.\n"
    return msg


async def mp_addRef(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match, check_tourney_host=False, check_referee=False):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp addref <ref username>"

    to_token = Context.players.get_token(name=args[1].strip().lower())
    if not to_token:
        return "Player not found/not online"

    if to_token not in player.match.channel.users:
        return "User not in lobby"

    if to_token.id in player.match.referees:
        return (
            f"This referee added already :) He can join with command !mp join {player.match.id}"
        )

    player.match.referees.append(to_token.id)
    return f"Added {to_token.id} to match referee. He can join with command !mp join {player.match.id}"


async def mp_removeRef(args: List[str], player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match, check_tourney_host=False, check_referee=False):
        return "You cant do anything with that match"

    if len(args) < 2:
        return "Wrong syntax: !mp removeref <ref username>"

    to_token = Context.players.get_token(name=args[1].strip().lower())
    if not to_token:
        return "Player not found/not online"

    if to_token not in player.match.channel.users:
        return "User not in lobby"

    if to_token.id not in player.match.referees:
        return "This user is not referre."

    player.match.referees.remove(to_token.id)
    await player.match.channel.leave_channel(to_token)
    return "Match referee was deleted!"


async def mp_history(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    match = player.match
    if not match.vinse_id:
        return "Match history not available, please play at least one map!"

    return f"Match history available [https://kurikku.pw/matches/{match.vinse_id} here]"


async def mp_juststart(_, player: "Player", __):
    if not player.match:
        return "You are not in any match"

    if not can_take_match(player, player.match):
        return "You cant do anything with that match"

    match = player.match
    match.need_load = 0
    await match.all_players_loaded()
    return "DORIME START!"


MP_SUBCOMMANDS = {
    "make": mp_make,
    "close": mp_close,
    "join": mp_join,
    "lock": mp_lock,
    "unlock": mp_unlock,
    "size": mp_size,
    "move": mp_move,
    "host": mp_host,
    "clearhost": mp_clear_host,
    "start": mp_start,
    "invite": mp_invite,
    "map": mp_map,
    "set": mp_set,
    "abort": mp_abort,
    "kick": mp_kick,
    "password": mp_password,
    "randompassword": mp_random_password,
    "mods": mp_mods,
    "team": mp_team,
    "scorev": mpScoreV,
    "settings": mp_settings,
    "addref": mp_addRef,
    "removeref": mp_removeRef,
    "timer": mp_timer,
    "aborttimer": mp_abort_timer,
    "history": mp_history,
    "juststart": mp_juststart,
}


@CrystalBot.register_command("!mp")
async def roll(args: List[str], player: "Player", message: "Message"):
    if not args:
        return "Enter subcommand"

    subcommand = args[0].lower().strip()
    command = MP_SUBCOMMANDS.get(subcommand, None)
    if not command:
        return "Invalid subcommand"

    return await command(args, player, message)
