#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2014, Leszek Krupiński <leafnode@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import re

DOCUMENTATION = '''
---
module: pear
short_description: Manages PHP PEAR library dependencies.
description:
     - "Manage PHP PEAR dependencies. To use this module, one of the following keys is required: C(name)
       or C(channel)."
version_added: "0.1"
options:
  name:
    description:
      - The name of a PEAR library to install.
    required: false
    default: null
  version:
    description:
      - Version of a package to install. If version is omitted, newest version of a package will be installed.
    required: false
    default: null
  channel:
    description:
      - URL of a PEAR channel to add.
    required: false
    default: null
  state:
    description:
      - Desired state of a package or channel.
    required: false
    default: present
    choices: [ "present", "absent" ]
notes:
   - PEAR package manager has to be installed on a remote host. 
requirements: [ "pear" ]
author: Leszek Krupiński
'''

EXAMPLES = '''
# Install Log PEAR package
- pear: name=Log

# Uninstall Net_DNS2 package
- pear: name=Net_DNS2 state=absent

# Add pear.symfony.com PEAR channel
- pear: channel=pear.symfony.com

# Remove pear.symfony.com PEAR channel
- pear: channel=pear.symfony.com state=absent
'''

def _get_full_name(name, version=None):
    if version is None:
        resp = name
    else:
        resp = name + '-' + version
    return resp

def _is_package_present(module, name, version):
    rc, out_pear, err_pear = module.run_command('pear list')

    if rc != 0:
        module.fail_json()

    installed_pkgs = out_pear.split("\n")[3:]

    for pkg in installed_pkgs:
        try:
            [pkg_name, pkg_version, pkg_status] = re.split('\s+', pkg)
        except:
            pass

        if pkg_name == name and (version is None or version == pkg_version):
            return True

    return False


def _is_channel_present(module, name):
    rc, out_pear, err_pear = module.run_command('pear list-channels')

    if rc != 0:
        module.fail_json()

    installed_channels = out_pear.split("\n")[3:]

    for channel in installed_channels:
        try:
            [channel_url, channel_alias, channel_description] = re.split('\s+', channel, 2)
        except:
            pass

        if channel_url == name:
            return True

    return False

def _fail(module, cmd, out, err, rc = None):
    msg = ''
    if out:
        msg += "stdout: %s" % (out, )
    if err:
        msg += "\n:stderr: %s" % (err, )
    if rc:
        msg += "\nrc: %s" % (rc,)
    module.fail_json(cmd=cmd, msg=msg)


def main():
    package_state_map = dict(
        present='install',
        absent='uninstall'
    )

    channel_state_map = dict(
        present='channel-discover',
        absent='channel-delete'
    )

    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', choices=package_state_map.keys()),
            name=dict(default=None, required=False),
            version=dict(default=None, required=False),
            channel=dict(default=None, required=False),
        ),
        required_one_of=[['name', 'channel']],
        mutually_exclusive=[['name', 'channel']],
        supports_check_mode=True
    )

    state = module.params['state']
    name = module.params['name']
    version = module.params['version']
    channel = module.params['channel']

    err = ''
    out = ''

    if name:
        cmd = 'pear %s %s' % (package_state_map[state], _get_full_name(name, version))
    elif channel:
        cmd = 'pear %s %s' % (channel_state_map[state], channel)
    else:
        module.fail_json(msg='not enough parameters')
    
    if module.check_mode:
        if name:            
            is_present = _is_package_present(module, name, version)
            changed = (state == 'present' and not is_present) or (state == 'absent' and is_present)
            module.exit_json(changed=changed, stdout=out, stderr=err)
        elif channel:
            is_present = _is_channel_present(module, channel)
            changed = (state == 'present' and not is_present) or (state == 'absent' and is_present)
            module.exit_json(changed=changed, stdout=out, stderr=err)

    if name:
        present = _is_package_present(module, name, version)
        if state == 'present' and present or state == 'absent' and not present:
            module.exit_json(changed=False, name=name, version=version)

    rc, out_pear, err_pear = module.run_command(cmd)
    out += out_pear
    err += err_pear

    if name:
        if rc == 0 and state == 'absent' and 'not installed' in out_pear:
            pass
        elif rc == 1 and state == 'present' and 'already installed' in out_pear:
            pass
        elif rc != 0:
            _fail(module, cmd, out, err)

        if state == 'absent':
            changed = 'uninstall ok' in out_pear
        else:
            changed = 'install ok' in out_pear
    elif channel:
        if rc == 1 and state == 'present' and 'is already initialized' in out_pear:
            changed = False
        elif rc == 1 and state == 'absent' and 'does not exist' in out_pear:
            changed = False
        elif rc == 0 and state == 'present' and 'succeeded' in out_pear:
            changed = True
        elif rc == 0 and state == 'absent' and 'deleted' in out_pear:
            changed = True
        elif rc == 1:
            _fail(module, cmd, out, err, rc)

    module.exit_json(changed=changed, cmd=cmd, name=name, version=version,
                     state=state, channel=channel, stdout=out, stderr=err)

# import module snippets
from ansible.module_utils.basic import *

main()
