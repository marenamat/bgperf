# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gobgp import GoBGP
import os
from  settings import dckr
import yaml
import json
from threading import Thread
import time
import datetime

def rm_line():
    print('\x1b[1A\x1b[2K\x1b[1D\x1b[1A')

class Monitor(GoBGP):

    CONTAINER_NAME = 'bgperf_monitor'

    def run(self, conf, dckr_net_name=''):
        ctn = super(GoBGP, self).run(dckr_net_name)
        config = {}
        config['global'] = {
            'config': {
                'as': conf['monitor']['as'],
                'router-id': conf['monitor']['router-id'],
            },
        }
        config ['neighbors'] = [{'config': {'neighbor-address': conf['target']['local-address'],
                                            'peer-as': conf['target']['as']},
                                 'transport': {'config': {'local-address': conf['monitor']['local-address']}},
                                 'timers': {'config': {'connect-retry': 10}}}]
        with open('{0}/{1}'.format(self.host_dir, 'gobgpd.conf'), 'w') as f:
            f.write(yaml.dump(config))
        self.config_name = 'gobgpd.conf'
        startup = '''#!/bin/bash
ulimit -n 65536
gobgpd -t yaml -f {1}/{2} -l {3} > {1}/gobgpd.log 2>&1
'''.format(conf['monitor']['local-address'], self.guest_dir, self.config_name, 'info')
        filename = '{0}/start.sh'.format(self.host_dir)
        with open(filename, 'w') as f:
            f.write(startup)
        os.chmod(filename, 0o777)
        i = dckr.exec_create(container=self.name, cmd='{0}/start.sh'.format(self.guest_dir))
        dckr.exec_start(i['Id'], detach=True, socket=True)
        self.config = conf
        return ctn

    def local(self, cmd, stream=False):
        i = dckr.exec_create(container=self.name, cmd=cmd)
        return dckr.exec_start(i['Id'], stream=stream)

    def wait_established(self, neighbor):
        n = 0
        while True:
            if n > 0:
                 rm_line()
            print(f"Waiting {n} seconds for monitor")

            try:
                neigh = json.loads(self.local('gobgp neighbor {0} -j'.format(neighbor)).decode('utf-8'))
            except Exception as e:
                print(f"Monitor reading exception: {e}")
                continue

            if ((neigh['state']['session_state'] == 'established') or
                (neigh['state']['session_state'] == 6)):

                return n
            time.sleep(1)

            n = n+1

    def stats(self, queue):
        self.stop_monitoring = False
        def stats():
            cps = self.config['monitor']['check-points'] if 'check-points' in self.config['monitor'] else []

            while True:
                if self.stop_monitoring:
                    return

                try:
                    info = json.loads(self.local('gobgp neighbor -j').decode('utf-8'))[0]
                except Exception as e:
                    print(f"Monitor reading exception: {e}")
                    continue

                info['who'] = self.name
                state = info['afi_safis'][0]['state']
                if 'accepted'in state and len(cps) > 0 and int(cps[0]) <= int(state['accepted']):
                    cps.pop(0)
                    info['checked'] = True
                else:
                    info['checked'] = False
                info['time'] = datetime.datetime.now()
                queue.put(info)
                time.sleep(1)

        t = Thread(target=stats)
        t.daemon = True
        t.start()

