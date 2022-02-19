from blob import Context
from handlers.decorators import OsuEvent
from objects.BanchoObjects import Message
from packets.OsuPacketID import OsuPacketID

from typing import TYPE_CHECKING

from packets.Reader.PacketResolver import PacketResolver

if TYPE_CHECKING:
    from objects.Player import Player


# client packet: 87, bancho response: message
@OsuEvent.register_handler(OsuPacketID.Client_Invite)
async def match_change_team(packet_data: bytes, token: "Player"):
    if not token.match:
        return False

    user_id = await PacketResolver.read_user_id(packet_data)
    to = Context.players.get_token(uid=user_id)
    msg = Message(
        sender=token.name,
        to=to.name,
        body=f"Come join to my game: [osump://{token.match.id}/{token.match.password if token.match.password else ''} {token.match.name}]",
        client_id=token.id,
    )
    await token.send_message(msg)
    return True
