# CROP

Expanded: Cloudformation'd Repeatable Operator Packages

1. Signed, verifiable versions & artifacts
1. Easy deployment from a master function that will run stack updates to
   templates it controls

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

A package will have to contain one (or multiple) CloudFormation templates that
define its infrastructure, and a parameter spec for all the parameters that
need to be provided (this could just be generated based on CFN).

The package will a zipfile signed by the code signing keys (see Signatures) and
inside the package there will also be a list of the Lambda sha256 sums that are
expected to be deployed. Before running the template, the deployment script
will check the SHAs of all the Lambda zips as well as the full package to make
sure nothing was tampered with in-flight.

```
- foo.zip
  - crop-manifest.yml
  - template.[json,yaml,yml]
  - template.signature
  - hashes.txt
  - hashes.signature
```

## Signatures

Using [ed25519][ed25519], a variant of the Curve25519 elliptic curve used in
Diffie-Hellman exchanges, we'll be able sign artifacts so that they are:

- Fast to verify because we'll be doing so inside FaaS
- Portable, since we'll need to do these checks in a variety of environments
- Easy to post multiple places

PyNaCL, which provides bindings to the [nacl][nacl] crypto library, hits all
these requirements. Tentatively, we'll be using [signify][signify], which is
also used by the OpenBSD project to sign releases. There's a
[portable][portable_signify] version available, which works in Lambda and is
tested against the BSD original. If `signify` fails for some reason,
[PyNaCL][pynacl] has support for the same signature algorithm, and would be
able to read similar signature formats.

### Trust/Verification Process

The main goal is to allow users to trust that only allowable, vetted updates
will get deployed. Because of this, software authors will each get keys and the
user can set how many keys they require a release to be signed with before a
deploy.

For example, a user could decide not to verify signatures, or decide to require
at least 3 signatures out of a given list. The valid public keys will be
distributed with the master function that is responsible for deployments, and
will require manual intervention by the user/admin to be changed.

### Why No GPG?

At first, GPG/PGP was the frontrunner for the signing method, but there are a
few problems.

First, the web of trust isn't actually needed here. CROP is for
author-to-consumer distribution, not peer-to-peer messages. Look at how
`yum`/`dnf` and `apt` work. The distro (or repo owner) publish a key, which is
imported at install-time or included with the OS image. There's no web of
trust. If a user wants to make sure they got what they were supposed to, they
cross-check public keys with different sources or (more likely) can't figure
out how to import keys*.

Second, portability is a bit of a struggle. Even with statically compiled GPG,
it's a pain to get the keys imported to the right places and have it actually
work.

\* I have to look up how to import keys to my keyring *every single time*

### PyPi?

Python's [wheel][wheel] format has signing capabilities, but the signature must
be embedded in the wheel file, and there's no key rotation support or support
for multiple signatures.

### What About Signet?

[Signet][signet] is a code-signing system for Python that builds hashes of a
script and all its dependencies, then adds a custom loader that verifies the
hashes at runtime. This is overkill in Lambda because it only takes zip
archives. So the easiest place to handle signatures is there: sign the
templates and zip files to be distributed, then you don't need code to
self-verify at runtime.


[signet]: http://jamercee.github.io/signet/
[ed25519]: https://ed25519.cr.yp.to/index.html
[nacl]: https://nacl.cr.yp.to/index.html
[wheel]: https://wheel.readthedocs.io/en/latest/
[portable_signify]: https://github.com/aperezdc/signify
[signify]: https://www.openbsd.org/papers/bsdcan-signify.html
[pynacl]: https://pynacl.readthedocs.io/en/latest/signing/
[yesterdaytabase]: https://github.com/ryansb/yesterdaytabase

