# -*- coding: utf-8 -*-
# Copyright 2016 Ryan Scott Brown <sb@ryansb.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from nacl.encoding import Base64Encoder
import nacl.signing

def parse_public_key(file_name):
    with open(file_name, 'r') as kfile:
        label, key_material, meta = kfile.read().split('\n')
    verify_key = nacl.signing.VerifyKey(key_material, Base64Encoder)
    print(verify_key.encode(Base64Encoder).decode('utf-8'))
    return verify_key


def parse_private_key(file_name):
    with open(file_name, 'r') as kfile:
        label, key_material, meta = kfile.read().split('\n')


def main():
    import sys
    try:
        key_name = sys.argv[1]
    except ValueError:
        print('Usage: gen_key.py [key name]')
        print('Key name must be alphanumeric with no spaces.')
        sys.exit(1)

    # generate a random signing key
    k = nacl.signing.SigningKey.generate()
    file_body = "{key_name} {visibility} key\n{key_material}\ncrop v0.0.1 generated, see docs for details."

    pub_file = file_body.format(key_name=key_name, visibility='public',
        key_material=k.encode(Base64Encoder).decode('utf-8'))
    priv_file = file_body.format(key_name=key_name, visibility='private',
        key_material=k.to_curve25519_private_key().encode(Base64Encoder).decode('utf-8'))
    with open('{}.crop.pub'.format(key_name), 'w') as f:
        f.write(pub_file)
    with open('{}.crop.secret'.format(key_name), 'w') as f:
        f.write(priv_file)

    parse_public_key(key_name + '.crop.pub')

if __name__ == '__main__':
    main()
