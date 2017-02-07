# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import os
import time
import random
import string

import boto3

from crop.logging import log

def get_product(name=None, product_id=None):
    service = boto3_client('servicecatalog')
    if name:
        product = next(
            p for p in
            service.search_products()['ProductViewSummaries']
            if p['Name'] == name
        )
        product_id = product['ProductId']

    return service.describe_product(Id=product_id)['ProductViewSummary']


def build_template_url(asset_bucket, template_key, object_version_id=None):
    s3 = boto3_client('s3')
    # get S3 regional bucket URL and build URL for template
    template_url = '{}/{}/{}'.format(s3.meta.endpoint_url, asset_bucket, template_key)
    if object_version_id is not None:
        template_url += '?versionId={}'.format(object_version_id)
    return template_url


def update_product_artifact(product_id, version, template_url, description):
    service = boto3_client('servicecatalog')

    token = generate_idempotency_token()

    log.info('provisioning_artifact.create.start', token=token, product=product_id, object_url=template_url)

    artifact = service.create_provisioning_artifact(
        ProductId=product_id,
        Parameters={
            'Name': version,
            'Description': description,
            'Info': {
                'LoadTemplateFromURL': template_url,
            },
            'Type': 'CLOUD_FORMATION_TEMPLATE',
        },
        IdempotencyToken=token,
    )
    artifact_id = artifact['ProvisioningArtifactDetail']['Id']
    log.debug('provisioning_artifact.create.sent', artifact_id=artifact_id, artifact=artifact)

    while True:
        time.sleep(3)
        log.debug('provisioning_artifact.poll', artifact_id=artifact_id)
        result = service.describe_provisioning_artifact(
            ProvisioningArtifactId=artifact_id,
            ProductId=product_id,
        )
        if result['Status'] == 'CREATING':
            log.debug('provisioning_artifact.incomplete', artifact_id=artifact_id, result=result)
            continue
        elif result['Status'] == 'FAILED':
            log.error('provisioning_artifact.failed',
                message='Failed to create artifact', product_id=product_id,
                artifact_id=artifact_id, result=result)
            raise Exception('Failed to create artifact {}, see logs for additional info'.format(artifact_id))
        elif result['Status'] == 'AVAILABLE':
            log.debug('provisioning_artifact.success', artifact_id=artifact_id, artifact=result)
            return artifact_id




def generate_idempotency_token():
    return ''.join(random.sample(string.ascii_letters*16, 16))


def boto3_client(service, **kwargs):
    return boto3.Session(
        profile_name=os.getenv('AWS_PROFILE')
    ).client(
        service,
        region_name=os.getenv('AWS_REGION'),
        **kwargs,
    )
