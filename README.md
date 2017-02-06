# CROP

Expanded name: Cloudformation'd Repeatable Operator Packages

1. Versioned, repeatable artifacts
1. Easy deployment from a Serverless Framework project to an AWS Service
   Catalog product.

## What?

CROP is a tool to make it easy to ship around the bundles of code,
configuration, and metadata that make up many applications deployed to AWS. The
AWS Service Catalog handles some of this work by using CloudFormation
templates as an application spec, and layering on a notion of portfolios
(groups of products) and roles (delegated perms to deploy those products). CROP
is intended to make the use of the Service Catalog easier for projects that use
the Serverless Framework.

To do this, CROP operates as a Serverless Plugin or as a stand-alone CLI tool
that modifies the behavior of `serverless deploy` to ship artifacts to a
Service Catalog product instead of live infrastructure. Custom template items
are easy to add in the `serverless.yml` if your app needs EC2 instances,
queues, or any other AWS resource in addition to Lambdas. CROP puts them
together in one artifact, and make it easy to move them across accounts or
build-run boundaries in your organization.

## Use Case Sample

Take for example the [yesterdaytabase][yesterdaytabase] project. The basic idea
is to take snapshots of prod data, then roll them out to staging environments
for developers to use as a sandbox.

There's *some* data that the user needs to provide (information about their
subnets, preference for DNS name, instance to copy), but the CloudFormation and
Lambda code to do the work remains the same. We also want to make "day 2"
management of this software easy. It's not strictly SaaS, since the code is
running in a *user/customer* AWS account and they'll be interested in
maintaining their control. Even so, the author should be able to provide
(automatic) updates to the code or template.

So there has to be:

- Some way to surface requests to the operator to ask them to approve updates
- Signatures so they have faith they're getting the right software
- Idempotent, rollback-friendly updates (CloudFormation covers this)
- A schedule for "phoning home" to check for updates

## Package Contents

A package will have to contain a CloudFormation template and point to a known,
public (or semipublic) bucket containing the code zipfiles. In CFN, all the
Lambda functions will be pointed to the CodeSha256 matching the S3 objects to
avoid deploying incorrect application versions, no matter when the product is
launched.

[yesterdaytabase]: https://github.com/ryansb/yesterdaytabase

