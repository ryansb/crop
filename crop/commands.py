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

    product_info = utils.get_product(
        name=config['product'].get('name'),
        product_id=config['product'].get('id'),
    )
    product_id = product_info['ProductId']

    project_dir = config.get(
        'project_path',
        dirname(abspath(arguments['--config']))
    )
    serverless_dir = join(project_dir, '.serverless')
    asset_s3_prefix = "{}/assets/".format(product_id)

    log.bind(
        serverless_dir=serverless_dir,
        bucket=config['catalog']['bucket'],
        prefix=asset_s3_prefix,
    )

    template_key, template_version = munge.upload_project(
        serverless_dir,
        config['catalog']['bucket'],
        asset_s3_prefix,
    )

    artifact_id = utils.update_product_artifact(
        product_id,
        '2',
        utils.build_template_url(
            config['catalog']['bucket'],
            template_key,
            template_version
        )
    )
    log.info('update_product.success')
