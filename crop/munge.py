# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import os
import six
import json
from io import StringIO

import boto3
from crop.logging import log


def upload_project(serverless_dir, asset_bucket, asset_s3_prefix):
    zip_assets = asset_map(serverless_dir, asset_s3_prefix)
    versioned_assets = upload_zipfiles(serverless_dir, asset_bucket, zip_assets)

    with open(os.path.join(serverless_dir, 'cloudformation-template-update-stack.json')) as source_template:
        out_template = cloudformation_template(
            source_template.read(),
            asset_bucket,
            versioned_assets,
        )
    upload_template(out_template, asset_bucket, asset_s3_prefix)


def upload_zipfiles(serverless_dir, asset_bucket, asset_key_map):
    """Takes an asset key map and will return a new one with uploaded files. If
    the bucket has object versioning, the asset map returned will have versions
    in addition to keys"""
    s3 = boto3.client('s3')

    new_map = {}

    for fname, key in asset_key_map.items():
        log.debug('file.upload.start', name=fname, key=key, bucket=asset_bucket)
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
        log.debug('file.upload.success', name=fname, key=key, bucket=asset_bucket)
    log.info('assets.upload.success', map=new_map, bucket=asset_bucket)
    return new_map

def upload_template(template, asset_bucket, prefix):
    from io import StringIO
    s3 = boto3.client('s3')

    log.debug('template.upload.start', key=prefix + 'template.json', bucket=asset_bucket)
    resurlt = s3.put_object(
        ACL='public-read',
        Bucket=asset_bucket,
        Key=prefix + 'template.json',
        ContentType='application/json',
        Body=json.dumps(template, indent=2)
    )
    log.debug('template.upload.success', key=prefix + 'template.json', bucket=asset_bucket)
    return asset_bucket, prefix + 'template.json'

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
    if isinstance(template, six.text_type):
        template = json.loads(template)
        log.debug('template.parse')

    # Pop resources out of the template that create the bucket serverless would upload code to
    template['Resources'].pop('ServerlessDeploymentBucket')
    template['Outputs'].pop('ServerlessDeploymentBucketName')

    for logical_id, resource in template['Resources'].items():
        if resource["Type"] != "AWS::Lambda::Function":
            # then the resource doesn't have a code type, so we needn't modify it
            continue

        asset_name = os.path.basename(resource['Properties']['Code']['S3Key'])

        # Find the right asset key/version information
        new_code = {
            'S3Bucket': asset_bucket,
        }

        if isinstance(asset_key_map[asset_name], six.text_type):
            key = asset_key_map[asset_name]
            new_code['S3Key'] = key
        else:
            key, version = asset_key_map[asset_name]
            new_code['S3Key'] = key
            new_code['S3ObjectVersion'] = version

        # Modify the Lambda function to get its code from the distribution bucket
        resource['Properties']['Code'] = new_code
        log.debug('resource.munge', logical_resource=logical_id, resource=resource)

    return template


def asset_map(serverless_dir, prefix):
    assets = {
        i: prefix + i for i in
        os.listdir(serverless_dir)
        if i.endswith('.zip')
    }
    log.debug('munge.asset_map', assets=assets)
    return assets
