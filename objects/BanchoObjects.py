from collections import namedtuple

Message = namedtuple('Message', ("sender", "to", "body", "client_id"))
