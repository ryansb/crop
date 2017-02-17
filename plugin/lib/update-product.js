'use strict';

const _ = require('lodash');
const child = require('child_process');
const BbPromise = require('bluebird');
const utils = require('./utils');

function invokeCrop(serverless, args) {
  var cmd = child.spawnSync(
    'crop', args, {stdio: 'pipe'}
  );
  if (cmd.status !== 0) {
    serverless.cli.log(`Command to CROP exited ${cmd.status}`);
    serverless.cli.log(`Command was: crop ${args.join(' ')}`);
    serverless.cli.log(`STDERR: ${cmd.stderr}`);
    serverless.cli.log(`STDOUT: ${cmd.stdout}`);
    return {};
  }
  return JSON.parse(cmd.stdout);
}

function updateProduct (serverless, options) {
  const args = ['update-product']
  if (_.get(serverless, 'variables.service.custom.crop.config') !== undefined) {
    args.push('--config')
    args.push(_.get(serverless, 'variables.service.custom.crop.config'))
  }
  if (options.version) {
    args.push('--version')
    args.push(options.version)
  }
  if (options.description) {
    args.push('--description')
    args.push(options.description)
  }
  var result = utils.invokeCrop(serverless, args);

  serverless.cli.log(`RESULT ${JSON.stringify(result)}`);
}

function updateProduct (serverless, options) {
  const args = ['upload-project']
  if (_.get(serverless, 'variables.service.custom.crop.config') !== undefined) {
    args.push('--config')
    args.push(_.get(serverless, 'variables.service.custom.crop.config'))
  }
  if (options.version) {
    args.push('--version')
    args.push(options.version)
  }
  var result = utils.invokeCrop(serverless, args);

  serverless.cli.log(`RESULT ${JSON.stringify(result)}`);
}

module.exports = updateProduct;
