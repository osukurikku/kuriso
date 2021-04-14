Kuriso (w.i.p.) - powerful bancho for private osu!servers
===
[![Discord](https://discordapp.com/api/guilds/511199892031668245/widget.png?style=shield)](https://discord.gg/5uA3c76)
[![GitHub issues](https://img.shields.io/github/issues/osukurikku/kuriso.svg)](https://github.com/osukurikku/kuriso/issues)
[![license](https://img.shields.io/github/license/osukurikku/kuriso.svg)](https://github.com/osukurikku/kuriso/blob/master/LICENSE)
[![CodeFactor](https://www.codefactor.io/repository/github/osukurikku/kuriso/badge)](https://www.codefactor.io/repository/github/osukurikku/kuriso)\
Future bancho of [kurikku.pw](https://kurikku.pw).\
Written in Python3.6 by [uvicorn](https://github.com/encode/uvicorn) and [starlette](https://github.com/encode/starlette)

**Fully compatible with ripple-servers**

Installation
---
Recommend version of python is `3.6.5`, `3.6.6`(most stable and tested versions)
```bash
$ python -m pip install -r requirements.txt
$ mv .env.example .env
$ nano .env
$ python index.py
```

Example of [nginx](https://github.com/osukurikku/kuriso/blob/master/ext/nginx_server.conf) usage as proxy

What is this?
---
Kuriso - is an improved version of the original Ripple [pep.py](https://github.com/osuripple/pep.py), which was closed in 2019. It inherited the original API, allowing it to be used with LETS and Hanayo. This bancho is much faster due to asynchronous python and can compete with its counterparts in terms of speed

What it handles?
- Client login
- General osu!Packets
- Multiplayer/Spectator
- Any messages between users
- osu!Tournament Client (BETA) (**NOT LAZER!**)

TODO:
---
- Databases/Caches storage connections
    * [x] Redis
    * [x] MySQL
- Base information about users
    * [x] Stats
    * [x] Update osu actions and etc...
- Chat
    * [x] Messages
    * [x] Channels
    * [x] DM
    * [x] Bot
- Multiplayer
    * [x] Lobby creation
    * [x] Lobby updating
    * [x] Lobby starting
    * [x] Match score updates
- Tournaments
    * [x] Handle osu-tourney
    * [x] Handle osu-tourney when it want to spectate user
- IRC
    * [ ] IRC server
    * [ ] Handle connections
- RipplePeppyAPI v1
    * [x] Implementation
- RipplePeppyAPI v2(delta preview)
    * [ ] Implementation (will not be implemented until first major version will be released)
