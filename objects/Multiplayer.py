from typing import List, Union
from typing import TYPE_CHECKING

from blob import Context
from objects.Channel import Channel
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from objects.constants.multiplayer import MatchScoringTypes, MatchTeamTypes, MatchTypes, MultiSpecialModes
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Player import Player


class Slot:
    __slots__ = ('status', 'team', 'mods', 'token', 'skipped', 'loaded')

    def __init__(self, status: SlotStatus = SlotStatus.Open, team: SlotTeams = SlotTeams.Neutral,
                 mods: Mods = Mods.NoMod, token: 'Player' = None, skipped: bool = False,
                 loaded: bool = False):
        self.status = status
        self.team = team
        self.mods = mods
        self.token = token
        self.loaded = loaded
        self.skipped = skipped


class Match:
    __slots__ = ('slots', 'id', 'name', 'password', 'beatmap_name', 'beatmap', 'beatmap_md5', 'beatmap_id',
                 'in_progress', 'mods', 'host', 'host_tourney', 'seed', 'need_load', 'channel', 'match_type',
                 'match_playmode', 'match_scoring_type', 'match_team_type', 'match_freemod')

    def __init__(self, id: int, name: str, password: Union[str, None] = "", host: 'Player' = None,
                 host_tourney: 'Player' = None):
        self.slots: List[Slot] = [Slot() for _ in range(0, 16)]
        self.id: int = id
        self.name: str = name
        self.password: str = password

        self.host: 'Player' = host
        self.host_tourney: 'Player' = host_tourney

        self.beatmap_name: str = ""
        self.beatmap_md5: str = ""
        self.beatmap_id: int = -1

        self.in_progress: bool = False
        self.mods: Mods = Mods.NoMod
        self.seed: int = 0
        self.need_load: int = 0

        self.channel: Channel = Channel(
            server_name=f"#multi_{self.id}",
            description=f"Channel for #multi_{self.id}",
            public_read=True,
            public_write=True,
            temp_channel=True
        )

        self.match_type: MatchTypes = MatchTypes.Standart
        self.match_playmode: GameModes = GameModes.STD
        self.match_scoring_type: MatchScoringTypes = MatchScoringTypes.Score
        self.match_team_type: MatchTeamTypes = MatchTeamTypes.HeadToHead
        self.match_freemod: MultiSpecialModes = MultiSpecialModes.Empty

    @property
    def is_freemod(self) -> bool:
        return self.match_freemod == MultiSpecialModes.Freemod

    @property
    def is_password_required(self) -> bool:
        return bool(self.password)

    @property
    def free_slot(self) -> Union[Slot, None]:
        for slot in self.slots:
            if slot.status == SlotStatus.Open:
                return slot

        return None

    async def unready_completed(self) -> bool:
        for slot in self.slots:
            if slot.status == SlotStatus.Complete:
                slot.status = SlotStatus.NotReady

        return True

    async def unready_everyone(self) -> bool:
        for slot in self.slots:
            if slot.status == SlotStatus.Ready:
                slot.status = SlotStatus.NotReady

        return True

    async def update_match(self) -> bool:
        info_packet = await PacketBuilder.UpdateMatch(self)
        for user in self.channel.users:
            Context.players.get_token(uid=user).enqueue(info_packet)

        return True

    async def join_player(self, player: 'Player', entered_password: str = None) -> bool:
        if player.match or \
                (self.is_password_required and self.password != entered_password):
            player.enqueue(await PacketBuilder.MatchJoinFailed())
            return False

        slot = self.free_slot
        if not slot:
            player.enqueue(await PacketBuilder.MatchJoinFailed())
            return False

        slot.status = SlotStatus.NotReady
        slot.token = player

        player.match = self
        player.enqueue(await PacketBuilder.MatchJoinSuccess(self))

        await self.update_match()
        await self.channel.join_channel(player)
        return True

    async def leave_player(self, player: 'Player') -> bool:
        pl_slot = None
        for slot in self.slots:
            if slot.token == player:
                pl_slot = slot

        if pl_slot:
            pl_slot.status = SlotStatus.Open
            pl_slot.token = None
            pl_slot.mods = Mods.NoMod
            pl_slot.team = SlotTeams.Neutral

        await self.channel.leave_channel(player)  # try to part user

        if len(self.channel.users) == 0:
            # опа ча, игроки поливали, дизбендим матч
            Context.matches.pop(self.id)  # bye match
            info_packet = await PacketBuilder.DisbandMatch(self)
            for user in Context.channels["#lobby"].users:
                if user == player.id:
                    continue  # ignore us, because we will receive it first
                Context.players.get_token(uid=user).enqueue(info_packet)
        else:
            await self.update_match()

        player.match = None
        return True

    async def start(self) -> bool:
        # Do not notice please variables names
        # it was 01:30 AM
        # TODO: refactor names
        dudes_who_ready_to_play: List['Player'] = []

        for slot in self.slots:
            if (slot.status & SlotStatus.HasPlayer) > 0 and slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing
                self.need_load += 1
                dudes_who_ready_to_play.append(slot.token)

        self.in_progress = True
        match_start_packet = await PacketBuilder.InitiateStartMatch(self)
        for dude in dudes_who_ready_to_play:
            # enqueue MatchStart
            dude.enqueue(match_start_packet)

        return True
