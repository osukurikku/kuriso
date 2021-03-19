import json
import random
import time
from typing import List, Union
from typing import TYPE_CHECKING

from blob import Context
from bot.bot import CrystalBot
from objects.Channel import Channel
from objects.constants.GameModes import GameModes
from objects.constants.Modificators import Mods
from objects.constants.Slots import SlotStatus, SlotTeams
from objects.constants.multiplayer import MatchScoringTypes, MatchTeamTypes, MatchTypes, MultiSpecialModes
from packets.Builder.index import PacketBuilder

if TYPE_CHECKING:
    from objects.Player import Player


class Slot:
    __slots__ = ('status', 'team', 'mods', 'token', 'skipped', 'loaded', 'failed', "passed", 'score')

    def __init__(self, status: SlotStatus = SlotStatus.Open, team: SlotTeams = SlotTeams.Neutral,
                 mods: Mods = Mods.NoMod, token: 'Player' = None, skipped: bool = False,
                 loaded: bool = False):
        self.status = status
        self.team = team
        self.mods = mods
        self.token = token
        self.loaded = loaded
        self.skipped = skipped
        self.failed = False
        self.passed = True
        self.score = 0

    def toggle_ready(self):
        self.status = SlotStatus.Ready

    def toggle_unready(self):
        self.status = SlotStatus.NotReady

    def lock_slot(self) -> bool:
        if self.status & SlotStatus.HasPlayer:
            self.mods = Mods.NoMod
            self.token = None
            self.status = SlotStatus.Locked
            self.team = SlotTeams.Neutral
        else:
            self.status = SlotStatus.Locked
        return True

    def unlock_slot(self) -> bool:
        self.status = SlotStatus.Open
        return True

    def toggle_slot(self) -> bool:
        if self.status == SlotStatus.Locked:
            self.status = SlotStatus.Open
        elif self.status & SlotStatus.HasPlayer:
            self.mods = Mods.NoMod
            self.token = None
            self.status = SlotStatus.Locked
            self.team = SlotTeams.Neutral
        else:
            self.status = SlotStatus.Locked

        return True


class Match:
    __slots__ = ('slots', 'id', 'name', 'password', 'beatmap_name', 'beatmap', 'beatmap_md5', 'beatmap_id',
                 'in_progress', 'mods', 'host', 'host_tourney', 'seed', 'need_load', 'channel', 'match_type',
                 'match_playmode', 'match_scoring_type', 'match_team_type', 'match_freemod', 'is_tourney', 'referees',
                 'is_locked', 'timer_force', 'timer_runned', 'vinse_id')

    def __init__(self, id: int, name: str, password: Union[str, None] = "", host: 'Player' = None,
                 host_tourney: 'Player' = None, is_tourney: bool = False):
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
        self.is_locked: bool = False
        self.mods: Mods = Mods.NoMod
        self.seed: int = 0
        self.need_load: int = 0

        self.channel: Channel = None

        self.match_type: MatchTypes = MatchTypes.Standart
        self.match_playmode: GameModes = GameModes.STD
        self.match_scoring_type: MatchScoringTypes = MatchScoringTypes.Score
        self.match_team_type: MatchTeamTypes = MatchTeamTypes.HeadToHead
        self.match_freemod: MultiSpecialModes = MultiSpecialModes.Empty

        self.is_tourney: bool = is_tourney
        self.referees: List[int] = []

        self.timer_force: bool = False
        self.timer_runned: bool = False

        self.vinse_id = 0

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

    def slots_with_status(self, status: SlotStatus) -> List[Slot]:
        res = []
        for slot in self.slots:
            if slot.status & status:
                res.append(slot)

        return res

    def get_slot(self, token: 'Player') -> Union[Slot, None]:
        for m_slot in self.slots:
            if m_slot.token == token:
                return m_slot

        return None

    async def unready_completed(self) -> bool:
        for slot in self.slots:
            if slot.status == SlotStatus.Complete:
                slot.status = SlotStatus.NotReady
                slot.score = 0
                slot.failed = False
                slot.passed = True

        return True

    async def unready_everyone(self) -> bool:
        for slot in self.slots:
            if slot.status == SlotStatus.Ready:
                slot.status = SlotStatus.NotReady

        return True

    async def update_match(self) -> bool:
        asked = []
        info_packet = await PacketBuilder.UpdateMatch(self)
        for user in self.channel.users:
            asked.append(user.id)
            user.enqueue(info_packet)

        info_packet_for_foreign = await PacketBuilder.UpdateMatch(self, False)
        for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
            if not user.is_in_lobby:
                continue
            if user.id in asked:
                continue  # we send this packet already

            user.enqueue(info_packet_for_foreign)

        return True

    async def enqueue_to_all(self, packet: bytes) -> bool:
        for user in self.channel.users:
            user.enqueue(packet)

        return True

    async def enqueue_to_specific(self, packet: bytes, status: SlotStatus) -> bool:
        for slot in self.slots:
            if slot.status & status:
                slot.token.enqueue(packet)

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

        player._match = self
        player.enqueue(await PacketBuilder.MatchJoinSuccess(self))

        await self.update_match()
        await self.channel.join_channel(player)
        return True

    async def leave_player(self, player: 'Player') -> bool:
        pl_slot = None
        for slot in self.slots:
            if slot.token == player:
                pl_slot = slot

        is_was_host = False
        if pl_slot:
            is_was_host = pl_slot.token == self.host if not self.is_tourney else pl_slot.token == self.host_tourney
            pl_slot.status = SlotStatus.Open
            pl_slot.token = None
            pl_slot.mods = Mods.NoMod
            pl_slot.team = SlotTeams.Neutral

        await self.channel.leave_channel(player)  # try to part user

        if len(self.channel.users) == 0:
            # опа ча, игроки поливали, дизбендим матч
            Context.matches.pop(self.id)  # bye match
            info_packet = await PacketBuilder.DisbandMatch(self)
            for user in Context.players.get_all_tokens(ignore_tournament_clients=True):
                if not user.is_in_lobby:
                    continue
                user.enqueue(info_packet)
        else:
            # case when host leaves the lobby
            if is_was_host:
                # randomly give host
                slot = None
                while not slot:
                    slot = random.choice(self.slots)
                    if not slot.status & SlotStatus.HasPlayer:
                        slot = None

                if not self.is_tourney:
                    self.host = slot.token
                    self.host.enqueue(await PacketBuilder.MatchHostTransfer())  # notify new host, that he become host
                else:
                    self.host_tourney = slot.token
                    self.host_tourney.enqueue(await PacketBuilder.MatchHostTransfer())

            await self.update_match()

        if player.is_tourneymode:
            player.id_tourney = -1
        player._match = None
        return True

    async def disband_match(self) -> bool:
        info_packet = await PacketBuilder.DisbandMatch(self)
        await self.enqueue_to_all(info_packet)

        return True

    async def force_size(self, size: int) -> bool:
        for i in range(0, size):
            if self.slots[i].status == SlotStatus.Locked:
                self.slots[i].status = SlotStatus.Open  # open <size> slots
        for i in range(size, 16):
            if self.slots[i].status & SlotStatus.HasPlayer:
                self.slots[i].mods = Mods.NoMod
                self.slots[i].token = None
                self.slots[i].status = SlotStatus.Locked
                self.slots[i].team = SlotTeams.Neutral
            else:
                self.slots[i].status = SlotStatus.Locked

        return True

    async def move_host(self, new_host: 'Player' = None, slot_ind: int = 0) -> bool:
        to_host = None
        if new_host and not slot_ind:
            for m_slot in self.slots:
                if m_slot.token == new_host:
                    to_host = m_slot
                    break

        if not new_host and slot_ind:
            to_host = self.slots[slot_ind]

        if not to_host:
            return False

        if not to_host.token:
            return False

        if self.is_tourney:
            self.host_tourney = to_host.token
            self.host_tourney.enqueue(await PacketBuilder.MatchHostTransfer())
        else:
            self.host = to_host.token
            self.host.enqueue(await PacketBuilder.MatchHostTransfer())

        await self.update_match()
        return True

    async def change_slot(self, from_token: 'Player', new_slot: int) -> bool:
        slot = self.slots[new_slot]
        if (slot.status & SlotStatus.HasPlayer) or slot.status == SlotStatus.Locked:
            return False

        currentSlot = self.get_slot(from_token)

        slot.mods = currentSlot.mods
        slot.token = currentSlot.token
        slot.status = currentSlot.status
        slot.team = currentSlot.team

        currentSlot.mods = Mods.NoMod
        currentSlot.token = None
        currentSlot.status = SlotStatus.Open
        currentSlot.team = SlotTeams.Neutral
        await self.update_match()
        return True

    async def start(self) -> bool:
        # Do not notice please variables names
        # it was 01:30 AM
        # TODO: refactor names
        dudes_who_ready_to_play: List['Player'] = []

        for slot in self.slots:
            if (slot.status & SlotStatus.HasPlayer) and slot.status != SlotStatus.NoMap:
                slot.status = SlotStatus.Playing
                self.need_load += 1
                dudes_who_ready_to_play.append(slot.token)

        self.in_progress = True
        match_start_packet = await PacketBuilder.InitiateStartMatch(self)
        for dude in dudes_who_ready_to_play:
            # enqueue MatchStart
            dude.enqueue(match_start_packet)

        return True

    async def removeTourneyHost(self) -> bool:
        if not self.host_tourney:
            return True

        self.host_tourney = None
        await self.update_match()
        return True

    async def all_players_loaded(self) -> bool:
        ready_packet = await PacketBuilder.AllPlayersLoaded()
        await self.enqueue_to_all(ready_packet)
        return True

    async def abort(self) -> bool:
        if not self.in_progress:
            return False

        for slot in self.slots_with_status(SlotStatus.Playing):
            slot.status = SlotStatus.NotReady
            slot.failed = True
            slot.score = 0

        await self.update_match()
        await self.enqueue_to_all(await PacketBuilder.MatchAborted())
        return True

    async def match_ended(self) -> bool:
        api_message = {
            "id": self.id,
            "name": self.name,
            "beatmap_id": self.beatmap_id,
            "mods": self.mods.value,
            "game_mode": self.match_playmode.value,
            "host_id": self.host.id if not self.is_tourney else self.host_tourney.id,
            "host_user_name": self.host.name,
            "game_type": self.match_type.value,
            "game_score_condition": self.match_scoring_type.value,
            "game_mod_mode": self.match_freemod.value,
            "scores": {}
        }

        # Add score info for each player
        for slot in self.slots:
            if slot.token and slot.status == SlotStatus.Complete:
                api_message["scores"][slot.token.id] = {
                    "score": slot.score,
                    "mods": slot.mods.value,
                    "failed": slot.failed,
                    "pass": slot.passed,
                    "team": slot.team.value,
                    "username": slot.token.name
                }

        ch_name = "#multi_{}".format(self.id)
        if not self.vinse_id:
            self.vinse_id = (int(time.time()) // (60 * 15)) << 32 | self.id
            await CrystalBot.ez_message(
                ch_name,
                f"Match history available [https://kurikku.pw/matches/{self.vinse_id} here]"
            )

        # If this is a tournament match, then we send a notification in the chat
        # saying that the match has completed.
        if self.is_tourney:
            await CrystalBot.ez_message(
                ch_name,
                "Match has just finished."
            )

        await Context.redis.publish(
            "api:mp_complete_match", json.dumps(api_message)
        )
        return True

    async def change_special_mods(self, free_mod: MultiSpecialModes) -> bool:
        if self.match_team_type == MatchTeamTypes.TagCoop:
            self.match_freemod &= ~MultiSpecialModes.Freemod

        if self.match_freemod != free_mod:
            if free_mod == MultiSpecialModes.Freemod:
                for slot in self.slots:
                    if slot.status & SlotStatus.HasPlayer:
                        slot.mods = self.mods & ~Mods.SpeedAltering

                self.mods &= Mods.SpeedAltering
            else:
                for slot in self.slots:
                    if slot.token and slot.token == self.host or slot.token == self.host_tourney:
                        self.mods = slot.mods | (self.mods & Mods.SpeedAltering)

        self.match_freemod = free_mod
        return True

    async def change_mods(self, new_mods: Mods, token: 'Player') -> bool:
        if self.is_freemod:
            if self.host == token or self.host_tourney == token:
                self.mods = new_mods & Mods.SpeedAltering

            self.get_slot(token).mods = new_mods & ~Mods.SpeedAltering
        else:
            if not (self.host == token or self.host_tourney == token):
                return False

            self.mods = new_mods

        return True
