# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import os
import yaml

import boto3
from voluptuous import Schema, Required, Optional, Match, IsDir
from voluptuous.error import Invalid

from . import logging


"""
The `crop.yml` configuration file consists of 5 options, only 4 of which are
currently used.

`project_path`: this is a file system path (relative or absolute) to a
                Serverless framework project

`bucket`:       this is the name of an Amazon S3 bucket where assets will be
                stored. Ideally, it should have versioning enabled. If
                versioning isn't enabled, only one fully usable CROP version
                will be available at a time. This is because zip files
                are stored in constant paths, so newer uploads
                overwrite old ones unless bucket versioning is used.

`catalog`;      this key is unused, since crop does not yet have any
                features for interacting with catalogs.

`product`:      the Service Catalog Product that crop will interact
                with. This option only has one attribute, `id`.

`upload`:       this option is expected to be used instead of `product`
                when not using Service Catalog, but just want a way to
                upload Serverless project artifacts without deploying
                them. This is useful for deploy pipelines, multistep
                deploys, and archival/audit purposes. This has only one
                attribute, `prefix`, and it is defaulted to an empty
                string.

Example Configuration:
project_path: foo/bar/serverlessproj
bucket: crop-assets-here
product:
  id: prod-123456
"""
schema = Schema({
    Optional('project_path'): IsDir(),
    Required('bucket'): str,
    Optional('catalog'): {
        Optional('id'): Match(r'^port-[A-Za-z0-9]+$'),
    },
    Optional('product'): {
        Required('id'): Match(r'^prod-[A-Za-z0-9]+$'),
    },
    Optional('upload'): {
        Optional('prefix', default=''): str
    }
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
