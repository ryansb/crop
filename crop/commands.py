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

    log.bind(
        serverless_dir=serverless_dir,
        bucket=config['bucket'],
    )

    template_key, template_version = munge.upload_serverless_artifacts(
        serverless_dir=serverless_dir,
        asset_bucket=config['bucket'],
        zipfile_s3_prefix="assets/{}/".format(product_id),
        template_s3_prefix="templates/{}/".format(product_id),
        project_version=arguments['--version'],
        product_id=product_id,
        autoupdate=config['autoupdate']
    )

    artifact_id = utils.update_product_artifact(
        product_id,
        arguments['--version'],
        utils.build_template_url(
            config['bucket'],
            template_key,
        ),
        description=arguments['--description']
    )
    log.info('update_product.success', artifact=artifact_id,
        template=template_key, bucket=config['bucket'])
    return {
        'command': 'update-product',
        'artifact': artifact_id,
        'template_url': utils.build_template_url(
            config['bucket'],
            template_key,
        ),
        'bucket': config['bucket'],
    }


def upload_project(config, arguments):
    log = logging.log.bind(method='upload_project')

    project_dir = config.get(
        'project_path',
        dirname(abspath(arguments['--config']))
    )

    serverless_dir = join(project_dir, '.serverless')

    log.info(
        'project.loaded',
        serverless_dir=serverless_dir,
        bucket=config['bucket'],
    )

    template_key, template_version = munge.upload_serverless_artifacts(
        serverless_dir=serverless_dir,
        asset_bucket=config['bucket'],
        zipfile_s3_prefix="{}/zipfiles/".format(config.get('upload', {}).get('prefix', '')),
        template_s3_prefix="{}/templates/".format(config.get('upload', {}).get('prefix', '')),
        project_version=arguments['--version'],
    )

    return {
        'command': 'upload-project',
        'template_url': utils.build_template_url(
            config['bucket'],
            template_key,
        ),
        'bucket': config['bucket'],
    }
