from typing import Union, Optional

from starlette.responses import HTMLResponse


class BanchoResponse(HTMLResponse):

    def __init__(self, response_text: Union[bytes], token: Optional[str] = None):
        headers = {
            'cho-token': '',
            'cho-protocol': '19',
            'Server': 'bancho',
            'connection': 'Keep-Alive',
            'vary': 'Accept-Encoding'
        }
        if token:
            headers['cho-token'] = token

        if len(response_text) < 1:
            response_text = b""

        super().__init__(content=response_text, status_code=200, headers=headers)
