"""Install the local Ubuntu Engine using Docker's official apt repository."""
import os
import platform
import re
import subprocess

CONFLICTS = ('docker.io', 'docker-compose', 'docker-compose-v2', 'docker-doc',
             'docker-buildx', 'podman-docker', 'containerd', 'runc')


def installed_conflicts():
    result = subprocess.run(['dpkg', '--get-selections'], capture_output=True, text=True, check=True)
    return [parts[0] for line in result.stdout.splitlines()
            if len(parts := line.split()) == 2 and parts[1] in ('install', 'hold')
            and parts[0].split(':')[0] in CONFLICTS]


def repository_plan(codename, architecture, conflicts=(), privileged=False):
    if not re.fullmatch(r'[a-z][a-z0-9]*', codename) or not re.fullmatch(r'[a-z0-9]+', architecture):
        raise ValueError('Invalid Ubuntu codename or architecture')
    if any(package.split(':')[0] not in CONFLICTS for package in conflicts):
        raise ValueError('Unexpected conflicting package')
    prefix = [] if privileged else ['sudo']
    steps = []
    if conflicts:
        steps.append((prefix + ['apt-get', 'remove', *conflicts], None))
    steps += [(prefix + command, None) for command in (
        ['apt-get', 'update'], ['apt-get', 'install', '-y', 'ca-certificates', 'curl'],
        ['install', '-m', '0755', '-d', '/etc/apt/keyrings'],
        ['curl', '-fsSL', 'https://download.docker.com/linux/ubuntu/gpg', '-o', '/etc/apt/keyrings/docker.asc'],
        ['chmod', 'a+r', '/etc/apt/keyrings/docker.asc'],
    )]
    source = ('Types: deb\nURIs: https://download.docker.com/linux/ubuntu\n'
              f'Suites: {codename}\nComponents: stable\nArchitectures: {architecture}\n'
              'Signed-By: /etc/apt/keyrings/docker.asc\n')
    steps += [(prefix + ['tee', '/etc/apt/sources.list.d/docker.sources'], source),
              (prefix + ['apt-get', 'update'], None)]
    return steps


def package_command(version='', privileged=False):
    if version and not re.fullmatch(r'[0-9][A-Za-z0-9.+:~_-]*', version):
        raise ValueError('Invalid Docker package version')
    suffix = f'={version}' if version else ''
    return ([] if privileged else ['sudo']) + [
        'apt-get', 'install', '-y', f'docker-ce{suffix}', f'docker-ce-cli{suffix}',
        'containerd.io', 'docker-buildx-plugin', 'docker-compose-plugin']


def run_step(command, content=None, dry_run=False):
    print(('** Preview ** ' if dry_run else '==> ') + ' '.join(command), flush=True)
    if content:
        print(content)
    if not dry_run:
        subprocess.run(command, input=content, text=True, check=True)


def install_docker(dry_run=False, choose_version=False, hello_world=False, group_user=''):
    """Returns False on failure/cancellation; never switches the active Docker context."""
    try:
        privileged = hasattr(os, 'geteuid') and os.geteuid() == 0
        prefix = [] if privileged else ['sudo']
        if group_user and not re.fullmatch(r'[a-z_][a-z0-9_-]*[$]?', group_user):
            raise ValueError('Invalid username')
        release = platform.freedesktop_os_release()
        if release.get('ID') != 'ubuntu':
            raise ValueError('Direct installation is available on Ubuntu only.')
        codename = release.get('UBUNTU_CODENAME') or release.get('VERSION_CODENAME', '')
        architecture = subprocess.run(['dpkg', '--print-architecture'], capture_output=True,
                                      text=True, check=True).stdout.strip()
        conflicts = installed_conflicts()
        steps = repository_plan(codename, architecture, conflicts, privileged)
        print('Conflicting packages detected: ' + (', '.join(conflicts) or 'None'))
        if conflicts:
            print('Removing packages may stop services that depend on them. apt will display removal details and request confirmation.')
        for command, content in steps:
            run_step(command, content, dry_run=True)
        run_step(package_command(privileged=privileged), dry_run=True)
        print('After installation: start service and verify local engine, Compose, and Buildx.')
        if dry_run:
            if choose_version:
                print('Available versions will be displayed and a version selected for each of docker-ce and docker-ce-cli after repository setup.')
            if hello_world:
                print('hello-world test: enabled')
            if group_user:
                print(f'Add user to docker group: {group_user}')
            return True
        if input('Execute installation plan on this machine? [y/N]: ').strip().lower() != 'y':
            return False
        for command, content in steps:
            run_step(command, content)
        version = ''
        if choose_version:
            available = []
            for package in ('docker-ce', 'docker-ce-cli'):
                result = subprocess.run(['apt-cache', 'madison', package], capture_output=True,
                                        text=True, check=True)
                available.append({line.split('|')[1].strip() for line in result.stdout.splitlines() if '|' in line})
            versions = sorted(available[0] & available[1], reverse=True)
            if not versions:
                raise ValueError('No common versions for engine and client in the repository.')
            print('\n'.join(versions))
            version = input('Copy the required VERSION_STRING, or 0 to cancel: ').strip()
            if version not in versions:
                print('Package installation cancelled; repository setup has already been done.')
                return False
        run_step(package_command(version, privileged))
        run_step(prefix + ['systemctl', 'start', 'docker'])
        run_step(prefix + ['systemctl', '--no-pager', '--full', 'status', 'docker'])
        docker = prefix + ['docker', '--host', 'unix:///var/run/docker.sock']
        run_step(docker + ['info'])
        run_step(docker + ['compose', 'version'])
        run_step(docker + ['buildx', 'version'])
        if hello_world:
            run_step(docker + ['run', '--rm', 'hello-world'])
        if group_user:
            run_step(prefix + ['usermod', '-aG', 'docker', group_user])
            print('Log out and log in again to activate group membership.')
        print('Docker Engine installation completed and local engine, Compose, and extensions verified.')
        return True
    except (OSError, ValueError, subprocess.CalledProcessError, KeyboardInterrupt) as exc:
        print(f'Installation stopped: {exc}. Some steps may have been executed; check output.')
        return False
