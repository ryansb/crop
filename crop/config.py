# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import os
import yaml

import boto3
from voluptuous import Schema, Required, Optional, Match, IsDir
from voluptuous.error import Invalid

from . import logging


schema = Schema({
    Optional('project_path'): IsDir(),
    Required('bucket'): str,
    Optional('catalog'): {
        Optional('id'): Match(r'^port-[A-Za-z0-9]+$'),
    },
    Required('product'): {
        Optional('id'): Match(r'^prod-[A-Za-z0-9]+$'),
        Optional('name'): str,
    },
})

def configure(config_path):
    log = logging.log.bind(config_path=config_path)
    try:
        f = open(os.path.expanduser(config_path))
    except FileNotFoundError as e:
        log.error('config.notfound', exc_info=e)
        return "Config file {} must exist and be readable".format(config_path)

    try:
        config = yaml.load(f)
    except yaml.parser.ParserError as e:
        f.close()
        log.error('config.bad_yaml', exc_info=e)
        return "YAML parsing failed - please check config syntax"
    else:
        f.close()

    log.info('config.parsed', config=config)
    try:
        conf = schema(config)
        if 'id' in conf['product'] or 'name' in conf['product']:
            return conf
        else:
            log.error('config.failed', error="Need a product name or ID", config=config)
            return "Failed to parse config. Must provide one of product.name or product.id"
    except Invalid as e:
        log.error('config.failed', error=str(e), config=config, exc_info=e)
        return "Invalid configuration format: {}".format(str(e))
