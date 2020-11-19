from enum import IntFlag, unique


@unique
class KurikkuPrivileges(IntFlag):
    Banned = 0
    Restricted = 1 << 1
    Public = 1 << 0
    Normal = 3
    Pending = 1 << 20

    Donor = 7
    Bat = 271
    ReplayModerator = 4351
    TournamentStaff = 2097419
    ChatMod = 786767
    CM = 3079679
    Developer = 3129343
    Owner = 7340031
