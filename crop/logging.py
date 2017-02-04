# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import datetime
import logging
import sys
from structlog import wrap_logger
from structlog.processors import JSONRenderer
from structlog.stdlib import filter_by_level

logging.basicConfig(
    level=logging.WARN,
    stream=sys.stderr,
    format='%(message)s',
)

def add_timestamp(_, __, event):
    event['timestamp'] = datetime.datetime.utcnow().isoformat()
    return event

log = wrap_logger(
    logging.getLogger('crop'),
    processors=[
        filter_by_level,
        add_timestamp,
        JSONRenderer(indent=2, sort_keys=True)
    ]
)
