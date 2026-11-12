#!/usr/bin/env python3
"""Offline checks for the inline systemd shell and bootstrap credential boundary."""
import os
import getpass
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
UNITS = ROOT / 'platform/units'


def commands(path):
    # All variable expansion in these shell bodies is deliberately escaped as $$
    # for systemd; test the resulting bash source without executing a host service.
    text = path.read_text().replace('\\\n', ' ')
    for line in text.splitlines():
        if line.startswith(('ExecStart=', 'ExecCondition=', 'ExecStopPost=')):
            yield shlex.split(line.split('=', 1)[1].replace('$$', '$'))


class InlineUnits(unittest.TestCase):
    def test_all_inline_shell_parses(self):
        for path in UNITS.glob('*.service'):
            for args in commands(path):
                if '/usr/bin/bash' in args:
                    with self.subTest(unit=path.name, command=args[0]):
                        subprocess.run(['bash', '-n', '-c', args[-1]], check=True)

    def test_readiness_ignores_not_yet_created_helm_kubeconfig(self):
        args = next(c for c in commands(UNITS / 'platform-k0s-bootstrap.service')
                    if c[0] == '/usr/bin/timeout')
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            k0s = directory / 'k0s'
            k0s.write_text('''#!/bin/bash
set -eu
# Embedded kubectl must not inherit the future Helm kubeconfig.
test -z "${KUBECONFIG+x}" || exit 7
case "$*" in
  *--raw=/readyz*) echo ok ;;
  *"get nodes"*) echo node/fixture ;;
  *) exit 8 ;;
esac
''')
            k0s.chmod(0o755)
            env = os.environ | {'KUBECONFIG': str(directory / 'absent-kubeconfig'),
                                'PATH': str(directory) + os.pathsep + os.environ['PATH']}
            subprocess.run(['bash', '-ec', args[-1]], env=env, timeout=5, check=True)

    def kubeconfig_fixture(self, directory, existing=False):
        directory = Path(directory)
        home = directory / 'home with spaces'
        home.mkdir()
        commands_dir = directory / 'bin'
        commands_dir.mkdir()
        (commands_dir / 'getent').write_text('''#!/bin/bash
echo "fixture:x:$(id -u):$(id -g)::$FIXTURE_HOME:/bin/bash"
''')
        (commands_dir / 'k0s').write_text('''#!/bin/bash
test -z "${KUBECONFIG+x}" || exit 7
test "$*" = "kubeconfig admin" || exit 8
echo "fixture admin kubeconfig"
''')
        for binary in commands_dir.iterdir():
            binary.chmod(0o755)
        config = home / '.kube/config'
        if existing:
            config.parent.mkdir()
            config.write_text('user-managed configuration\n')
        env = os.environ | {'PLATFORM_USER': getpass.getuser(), 'FIXTURE_HOME': str(home),
                            'KUBECONFIG': '/nonexistent/inherited-config',
                            'PATH': str(commands_dir) + os.pathsep + os.environ['PATH']}
        command = next(c for c in commands(UNITS / 'platform-kubeconfig@.service')
                       if 'getent passwd' in c[-1])
        subprocess.run(command, env=env, timeout=5, check=True, capture_output=True)
        return config

    def test_kubeconfig_has_private_permissions_and_user_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.kubeconfig_fixture(directory)
            self.assertEqual(config.read_text(), 'fixture admin kubeconfig\n')
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            self.assertEqual(config.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(config.stat().st_uid, os.getuid())
            self.assertEqual(list(config.parent.glob('.config.*')), [])

    def test_existing_user_kubeconfig_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.kubeconfig_fixture(directory, existing=True)
            self.assertEqual(config.read_text(), 'user-managed configuration\n')


if __name__ == '__main__':
    unittest.main()
