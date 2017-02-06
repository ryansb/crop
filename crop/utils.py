# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import random
import string

import boto3

from crop.logging import log

def get_product(name=None, product_id=None):
    service = boto3.client('servicecatalog')
    if name:
        product = next(
            p for p in
            service.search_products()['ProductViewSummaries']
            if p['Name'] == name
        )
        product_id = product['ProductId']

    return service.describe_product(Id=product_id)['ProductViewSummary']

def build_template_url(asset_bucket, template_key, version_id=None):
    s3 = boto3.client('s3')
    # get S3 regional bucket URL and build URL for template
    template_url = '{}/{}/{}'.format(s3.meta.endpoint_url, asset_bucket, template_key)
    if version_id is not None:
        template_url += '?versionId={}'.format(version_id)
    return template_url


def update_product_artifact(product_id, version, template_url):
    service = boto3.client('servicecatalog')

    token = generate_idempotency_token()

    log.info('provisioning_artifact.create.start', token=token, product=product_id, object_url=template_url)

    artifact = service.create_provisioning_artifact(
        ProductId=product_id,
        Parameters={
            'Name': version,
            'Description': 'Deploy artifact by CROP',
            'Info': {
                'LoadTemplateFromURL': template_url,
            },
            'Type': 'CLOUD_FORMATION_TEMPLATE',
        },
        IdempotencyToken=token,
    )
    log.debug('provisioning_artifact.create.success', artifact=artifact)

def generate_idempotency_token():
    return ''.join(random.sample(string.ascii_letters*16, 16))
