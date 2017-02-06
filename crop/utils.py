# -*- coding: utf-8 -*-
# Author: Ryan Scott Brown <sb@ryansb.com>
# License: Apache v2.0

import boto3

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
