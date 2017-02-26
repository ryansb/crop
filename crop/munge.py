# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import os
import six
import json
from io import StringIO

import boto3
from .logging import log
from . import utils
from . import filters


def upload_serverless_artifacts(serverless_dir, asset_bucket,
        zipfile_s3_prefix, template_s3_prefix, project_version, product_id, autoupdate):
    """Upload project zipfiles and template to S3

    This function also transforms the Serverless template to remove custom
    bucket and replace with newly uploaded asset paths. The returned tuple is
    the S3 key in the asset bucket for the template, and the S3 object version
    (or None if versioning is disabled).

    TODO: Handle custom artifacts from serverless.yml `package` directives
    """
    zip_assets = asset_map(serverless_dir, zipfile_s3_prefix)
    versioned_assets = upload_zipfiles(serverless_dir, asset_bucket, zip_assets)

    with open(os.path.join(serverless_dir, 'cloudformation-template-update-stack.json')) as source_template:
        out_template = cloudformation_template(
            json.load(source_template),
            asset_bucket,
            versioned_assets,
        )
    log.debug('template.rewritten', template=out_template)

    if autoupdate:
        if autoupdate['type'] == 'forced':
            out_template = filters.inject_autoupdate(out_template, True)
        elif autoupdate['type'] == 'enabled':
            out_template = filters.inject_autoupdate(out_template, False)

        log.debug('template.rewritten', template=out_template)

    template_s3_key, version = upload_template(out_template, asset_bucket, template_s3_prefix, project_version)
    return template_s3_key, version


def upload_zipfiles(serverless_dir, asset_bucket, asset_key_map):
    """Takes an asset key map and will return a new one with uploaded files. If
    the bucket has object versioning, the asset map returned will have versions
    in addition to keys"""
    s3 = utils.boto3_client('s3')

    new_map = {}

    for fname, key in asset_key_map.items():
        log.debug('file.upload.start', path=os.path.join(serverless_dir, fname), key=key, bucket=asset_bucket)
        with open(os.path.join(serverless_dir, fname), 'rb') as f:
            result = s3.put_object(
                ACL='public-read',
                Bucket=asset_bucket,
                Key=key,
                ContentType='application/zip',
                Body=f.read()
            )
            if result.get('VersionId'):
                new_map[fname] = key, result['VersionId']
            else:
                new_map[fname] = key
        log.debug('file.upload.success', name=fname, key=key, bucket=asset_bucket, version=result.get('VersionId', ''))
    log.info('assets.upload.success', map=new_map, bucket=asset_bucket)
    return new_map

def upload_template(template, asset_bucket, prefix, project_version):
    s3 = utils.boto3_client('s3')

    template_key = '{}template-{}.json'.format(prefix, project_version)

    log.debug('template.upload.start',
        key=template_key,
        bucket=asset_bucket
    )

    result = s3.put_object(
        ACL='public-read',
        Bucket=asset_bucket,
        Key=template_key,
        ContentType='application/json',
        Body=json.dumps(template, sort_keys=True)
    )
    log.debug('template.upload.success', key=template_key, bucket=asset_bucket, version=result.get('VersionId', ''))
    return template_key, result.get('VersionId')

def cloudformation_template(template, asset_bucket, asset_key_map):
    """This function takes a (text) template output by the Serverless framework

    Params:
    template: JSON or dict of CFN template
    asset_bucket: str name of the S3 bucket that consumers of the product will be able to access
    asset_key_map: dict of the keys/artifacts to be replaced and a string or 2-tuple of key&version

    {
        template: [JSON text here]
        asset_bucket: test_bucket,
        asset_key_map: {
            serverless/project/stage/datetime/artifact.zip: prod-123456/assets/datetime/artifact.zip,
            serverless/project/stage/datetime/artifact2.zip: (prod-123456/artifact2.zip, ver-123456)
        }
    }

    Returns: JSONified output of new template
    """
    if not isinstance(template, dict):
        template = json.loads(template)
        log.debug('template.parse')

    template = filters.pop_bucket(template)

    template = filters.replace_function_artifacts(
        template, asset_bucket, asset_key_map)

    return template


def asset_map(serverless_dir, prefix):
    assets = {
        i: prefix + i for i in
        os.listdir(serverless_dir)
        if i.endswith('.zip')
    }
    log.debug('munge.asset_map', assets=assets)
    return assets
