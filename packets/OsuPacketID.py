from enum import Enum, unique


@unique
class OsuPacketID(Enum):
    Client_SendUserStatus = 0
    Client_SendIrcMessage = 1
    Client_Exit = 2
    Client_RequestStatusUpdate = 3
    Client_Pong = 4
    Bancho_LoginReply = 5
    Bancho_CommandError = 6
    Bancho_SendMessage = 7
    Bancho_Ping = 8
    Bancho_HandleIrcChangeUsername = 9
    Bancho_HandleIrcQuit = 10
    Bancho_HandleOsuUpdate = 11
    Bancho_HandleUserQuit = 12
    Bancho_SpectatorJoined = 13
    Bancho_SpectatorLeft = 14
    Bancho_SpectateFrames = 15
    Client_StartSpectating = 16
    Client_StopSpectating = 17
    Client_SpectateFrames = 18
    Bancho_VersionUpdate = 19
    Client_ErrorReport = 20
    Client_CantSpectate = 21
    Bancho_SpectatorCantSpectate = 22
    Bancho_GetAttention = 23
    Bancho_Announce = 24
    Client_SendIrcMessagePrivate = 25
    Bancho_MatchUpdate = 26
    Bancho_MatchNew = 27
    Bancho_MatchDisband = 28
    Client_LobbyPart = 29
    Client_LobbyJoin = 30
    Client_MatchCreate = 31
    Client_MatchJoin = 32
    Client_MatchPart = 33
    Bancho_MatchJoinSuccess = 36
    Bancho_MatchJoinFail = 37
    Client_MatchChangeSlot = 38
    Client_MatchReady = 39
    Client_MatchLock = 40
    Client_MatchChangeSettings = 41
    Bancho_FellowSpectatorJoined = 42
    Bancho_FellowSpectatorLeft = 43
    Client_MatchStart = 44
    Bancho_MatchStart = 46
    Client_MatchScoreUpdate = 47
    Bancho_MatchScoreUpdate = 48
    Client_MatchComplete = 49
    Bancho_MatchTransferHost = 50
    Client_MatchChangeMods = 51
    Client_MatchLoadComplete = 52
    Bancho_MatchAllPlayersLoaded = 53
    Client_MatchNoBeatmap = 54
    Client_MatchNotReady = 55
    Client_MatchFailed = 56
    Bancho_MatchPlayerFailed = 57
    Bancho_MatchComplete = 58
    Client_MatchHasBeatmap = 59
    Client_MatchSkipRequest = 60
    Bancho_MatchSkip = 61
    Bancho_Unauthorised = 62
    Client_ChannelJoin = 63
    Bancho_ChannelJoinSuccess = 64
    Bancho_ChannelAvailable = 65
    Bancho_ChannelRevoked = 66
    Bancho_ChannelAvailableAutojoin = 67
    Client_BeatmapInfoRequest = 68
    Bancho_BeatmapInfoReply = 69
    Client_MatchTransferHost = 70
    Bancho_LoginPermissions = 71
    Bancho_FriendsList = 72
    Client_FriendAdd = 73
    Client_FriendRemove = 74
    Bancho_ProtocolNegotiation = 75
    Bancho_TitleUpdate = 76
    Client_MatchChangeTeam = 77
    Client_ChannelLeave = 78
    Client_ReceiveUpdates = 79
    Bancho_Monitor = 80
    Bancho_MatchPlayerSkipped = 81
    Client_SetIrcAwayMessage = 82
    Bancho_UserPresence = 83
    Client_UserStatsRequest = 85
    Bancho_Restart = 86
    Client_Invite = 87
    Bancho_Invite = 88
    Bancho_ChannelListingComplete = 89
    Client_MatchChangePassword = 90
    Bancho_MatchChangePassword = 91
    Bancho_BanInfo = 92
    Client_SpecialMatchInfoRequest = 93
    Bancho_UserSilenced = 94
    Bancho_UserPresenceSingle = 95
    Bancho_UserPresenceBundle = 96
    Client_UserPresenceRequest = 97
    Client_UserPresenceRequestAll = 98
    Client_UserToggleBlockNonFriendPM = 99
    Bancho_UserPMBlocked = 100
    Bancho_TargetIsSilenced = 101
    Bancho_VersionUpdateForced = 102
    Bancho_SwitchServer = 103
    Bancho_AccountRestricted = 104
    Bancho_RTX = 105
    Client_MatchAbort = 106
    Bancho_SwitchTourneyServer = 107
    Client_SpecialJoinMatchChannel = 108
    Client_SpecialLeaveMatchChannel = 109
