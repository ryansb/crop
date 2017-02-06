# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

from os.path import join, dirname, abspath

from . import munge, logging, utils

def product(config, arguments):
    if arguments['--update']:
        update_product(config, arguments)
    return {'command': 'product'}


def update_product(config, arguments):
    log = logging.log.bind(method='update_product')

    product = utils.get_product(
        name=config['product'].get('name'),
        product_id=config['product'].get('id'),
    )

    project_dir = config.get(
        'project_path',
        dirname(abspath(arguments['--config']))
    )
    serverless_dir = join(project_dir, '.serverless')
    asset_s3_prefix = "{}/assets/".format(product['ProductId'])

    log.bind(
        serverless_dir=serverless_dir,
        bucket=config['catalog']['bucket'],
        prefix=asset_s3_prefix,
    )

    munge.upload_project(
        serverless_dir,
        config['catalog']['bucket'],
        asset_s3_prefix,
    )

    log.info('update_product.success')
