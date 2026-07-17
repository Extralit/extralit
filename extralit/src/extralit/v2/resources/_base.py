from extralit.v2._api._transport import AsyncTransport


class ResourceBase:
    def __init__(self, transport: AsyncTransport):
        self._transport = transport
