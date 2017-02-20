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
            source_template.read(),
            asset_bucket,
            versioned_assets,
        )
    log.debug('template.rewritten', template=out_template)

    if autoupdate:
        if autoupdate['type'] == 'forced':
            out_template = inject_autoupdate(out_template, True)
        else if autoupdate['type'] == 'enabled':
            out_template = inject_autoupdate(out_template, False)

        log.debug('template.rewritten', template=out_template)

    template_s3_key, version = upload_template(out_template, asset_bucket, template_s3_prefix, project_version)
    return template_s3_key, version


def inject_autoupdate(template, product_id, forced=False):
    """Inject a Lambda Function (and possible CF Param) for auto updating the
    service based on polling. You can either force this update, or allow it to be optional,
    in which case it is set by a CF dropdown parameter when the user starts the stack from
    the service catalog.
    """


    if any((x in template['Resources'] for x in (
        'CROPAutoUpdaterRole',
        'CROPAutoUpdaterEvent',
        'CROPAutoUpdateLambdaPermissionAutoUpdaterEvent',
        'CROPAutoUpdaterFunction'
        ))):
        raise ValueError('Resource logical IDs conflict with keys used by CROP')

    if any((x in template['Params'] for x in (
        'AutoUpdates'
        ))):
        raise ValueError('Param IDs conflict with Param IDs used by CROP')

    if any((x in template['Conditions'] for x in (
        'CROPAutoUpdating'
        ))):
        raise ValueError('Condition IDs conflict with Conditions IDs used by CROP')

    # role
    template['Resources']['CROPAutoUpdaterRole'] = {
        'Type':'AWS::IAM::Role',
        'Properties': {
            # Add update policy
            'AssumeRolePolicyDocument': {
                'Statement': [
                    {
                        'Action': [
                            'sts:AssumeRole'
                        ],
                        'Effect': 'Allow',
                        'Principal': {
                            'Service': [
                                'lambda.amazonaws.com'
                            ]
                        }
                    }
                ],
                'Version': '2012-10-17'
            },
            'Policies': [{
                'PolicyName': 'AutoUpdateServiceCatalog',
                'PolicyDocument': {
                    'Statement': [{
                            'Action': [
                                '*'
                            ],
                            'Effect': 'Allow',
                            'Resource': ['*']
                        }],
                    'Version': '2012-10-17'
                }
            }]
        }
    }

    if(autoupdate['interval'] < 1):
        raise ValueError('Cannot specify an interval less than 1 (minute)')


    if(autoupdate['interval'] == 1):
        intervalString = '1 minute'
    else
        intervalString = '{} minutes'.format(autoupdate['interval'])

    # event
    template['Resources']['CROPAutoUpdaterEvent'] = {
        'Type':'AWS::Events::Rule',
        'Properties': {
            'ScheduleExpression': 'rate({})'.format(intervalString), # TODO: 15 minutes?
            'State': 'ENABLED',
            'Targets': [{
                    'Arn': {
                        'Fn::GetAtt': ['AutoUpdaterFunction', 'Arn']
                    },
                    'Id': 'autoUpdaterSchedule'
                }]
        }
    }

    # allow aws to invoke lambda with event
    template['Resources']['CROPAutoUpdateLambdaPermissionAutoUpdaterEvent'] = {
        'Type': 'AWS::Lambda::Permission',
        'Properties': {
            'Action': 'lambda:InvokeFunction',
            'FunctionName': {'Fn::GetAtt': ['AutoUpdaterFunction', 'Arn']},
            'Principal': 'events.amazonaws.com',
            'SourceArn': {'Fn::GetAtt': ['AutoUpdaterEvent', 'Arn']}
        }
    }

    template['Resources']['CROPAutoUpdaterFunction'] = {
        'Type':'AWS::Lambda::Function',
        'Properties': {
            'Code': {
                # TODO: Abstract this to other file so we still get syntax highlighting
                # Or allow custom inject to allow custom "reporting" functionality
                'ZipFile': 'StuffHere', #inline updater function

                # I think I have to paginate all of this to find all currently provisioned products...
                # http://boto3.readthedocs.io/en/latest/reference/services/servicecatalog.html?highlight=service%20catalog#ServiceCatalog.Client.list_record_history

            },
            'Description': 'AutoUpdater for ServiceCatalog Function',
            'Handler': 'index.handler',
            'MemorySize': '256',
            'Environment': {
                'Variables': {
                    'StackName': {'Ref': 'AWS::StackName'},
                    'ProductId': product_id
                }
            },
            'Role': {'Fn::GetAtt': ['AutoUpdaterRole', 'Arn']},
            'Runtime': 'python2.7',
            'Timeout': 30
        }
    }

    if not forced:
        template.setdefault('Parameters', {})
        template['Parameters']['AutoUpdates'] = {
            'Type': 'String',
            'Description': 'Allow the service to automatically update itself when an update is available, otherwise you must manually approve updates.',
            'AllowedValues': ['Enable', 'Disable'],
            'Default': 'Enable'
        }

        # conditionals on roles / event / lambda
        template.setdefault('Conditions', {})
        template['Conditions']['CROPAutoUpdating'] = {'Fn::Equals' : [{'Ref' : 'AutoUpdates'}, 'Enabled']}

        template['Resources']['CROPAutoUpdaterFunction']['Condition'] = 'CROPAutoUpdating'
        template['Resources']['CROPAutoUpdateLambdaPermissionAutoUpdaterEvent']['Condition'] = 'CROPAutoUpdating'
        template['Resources']['CROPAutoUpdaterEvent']['Condition'] = 'CROPAutoUpdating'
        template['Resources']['CROPAutoUpdaterRole']['Condition'] = 'CROPAutoUpdating'


    log.debug('template.inject_autoupdate', template=template)
    return template


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
    from io import StringIO
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
