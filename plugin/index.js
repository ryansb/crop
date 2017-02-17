'use strict';

const BbPromise = require('bluebird');

const updateProduct = require('./lib/update-product');

class ServerlessCropPlugin {
  constructor(serverless, options) {
    this.serverless = serverless;
    this.options = options;

    this.hooks = {
      //'before:deploy:compileFunctions': () => {
      'before:deploy:deploy': () => {
        BbPromise.bind(this)
          .then(() => updateProduct(this.serverless, this.options));
      },
    };
  }
}

module.exports = ServerlessCropPlugin;
