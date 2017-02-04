# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import datetime
import logging
import sys
from structlog import wrap_logger
from structlog.processors import JSONRenderer
from structlog.stdlib import filter_by_level
from structlog.processors import format_exc_info, TimeStamper

logging.basicConfig(
    level=logging.WARN,
    stream=sys.stderr,
    format='%(message)s',
)

log = wrap_logger(
    logging.getLogger('crop'),
    processors=[
        filter_by_level,
        TimeStamper(fmt="ISO", utc=False),
        format_exc_info,
        JSONRenderer(indent=2, sort_keys=True)
    ]
)
