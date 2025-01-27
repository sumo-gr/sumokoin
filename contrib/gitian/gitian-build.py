#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

gsigs = 'https://github.com/sumoprojects/gitian.sigs.git'
gbrepo = 'https://github.com/devrandom/gitian-builder.git'

def setup():
    global args, workdir
    programs = ['apt-cacher-ng', 'ruby', 'git', 'make', 'wget']
    if args.kvm:
        programs += ['python-vm-builder', 'qemu-kvm', 'qemu-utils']
    else:
        programs += ['lxc', 'debootstrap']
    if not args.no_apt:
        subprocess.check_call(['sudo', 'apt-get', 'install', '-qq'] + programs)
    if not os.path.isdir('sigs'):
        subprocess.check_call(['git', 'clone', gsigs, 'sigs'])
    if not os.path.isdir('builder'):
        subprocess.check_call(['git', 'clone', gbrepo, 'builder'])
    os.chdir('builder')
    subprocess.check_call(['git', 'config', 'user.email', 'gitianuser@localhost'])
    subprocess.check_call(['git', 'config', 'user.name', 'gitianuser'])
    subprocess.check_call(['git', 'checkout', '963322de8420c50502c4cc33d4d7c0d84437b576'])
    subprocess.check_call(['git', 'fetch', 'origin', '72c51f0bd2adec4eedab4dbd06c9229b9c4eb0e3'])
    subprocess.check_call(['git', 'cherry-pick', '72c51f0bd2adec4eedab4dbd06c9229b9c4eb0e3'])
    os.makedirs('inputs', exist_ok=True)
    os.chdir('inputs')
    if not os.path.isdir('sumokoin'):
        subprocess.check_call(['git', 'clone', args.url, 'sumokoin'])
    os.chdir('..')
    make_image_prog = ['bin/make-base-vm', '--suite', 'bionic', '--arch', 'amd64']
    if args.docker:
        if not subprocess.call(['docker', '--help'], shell=False, stdout=subprocess.DEVNULL):
            print("Please install docker first manually")
        make_image_prog += ['--docker']
    elif not args.kvm:
        make_image_prog += ['--lxc']
    subprocess.check_call(make_image_prog)
    os.chdir(workdir)
    if args.is_bionic and not args.kvm and not args.docker:
        subprocess.check_call(['sudo', 'sed', '-i', 's/lxcbr0/br0/', '/etc/default/lxc-net'])
        print('Reboot is required')
        sys.exit(0)

def rebuild():
    global args, workdir

    print('\nBuilding Dependencies\n')
    os.makedirs('../out/' + args.version, exist_ok=True)

    if args.linux:
        print('\nCompiling ' + args.version + ' Linux')
        subprocess.check_call(['bin/gbuild', '-j', args.jobs, '-m', args.memory, '--commit', 'sumokoin='+args.commit, '--url', 'sumokoin='+args.url, 'inputs/sumokoin/contrib/gitian/gitian-linux.yml'])
        subprocess.check_call(['bin/gsign', '-p', args.sign_prog, '--signer', args.signer, '--release', args.version+'-linux', '--destination', '../sigs/', 'inputs/sumokoin/contrib/gitian/gitian-linux.yml'])
        subprocess.check_call('mv build/out/sumokoin-*.tar.bz2 ../out/'+args.version, shell=True)

    if args.android:
        print('\nCompiling ' + args.version + ' Android')
        subprocess.check_call(['bin/gbuild', '-j', args.jobs, '-m', args.memory, '--commit', 'sumokoin='+args.commit, '--url', 'sumokoin='+args.url, 'inputs/sumokoin/contrib/gitian/gitian-android.yml'])
        subprocess.check_call(['bin/gsign', '-p', args.sign_prog, '--signer', args.signer, '--release', args.version+'-android', '--destination', '../sigs/', 'inputs/sumokoin/contrib/gitian/gitian-android.yml'])
        subprocess.check_call('mv build/out/sumokoin-*.tar.bz2 ../out/'+args.version, shell=True)

    if args.windows:
        print('\nCompiling ' + args.version + ' Windows')
        subprocess.check_call(['bin/gbuild', '-j', args.jobs, '-m', args.memory, '--commit', 'sumokoin='+args.commit, '--url', 'sumokoin='+args.url, 'inputs/sumokoin/contrib/gitian/gitian-win.yml'])
        subprocess.check_call(['bin/gsign', '-p', args.sign_prog, '--signer', args.signer, '--release', args.version+'-win', '--destination', '../sigs/', 'inputs/sumokoin/contrib/gitian/gitian-win.yml'])
        subprocess.check_call('mv build/out/sumokoin*.zip ../out/'+args.version, shell=True)

    if args.macos:
        print('\nCompiling ' + args.version + ' MacOS')
        subprocess.check_call(['bin/gbuild', '-j', args.jobs, '-m', args.memory, '--commit', 'sumokoin='+args.commit, '--url', 'sumokoin'+args.url, 'inputs/sumokoin/contrib/gitian/gitian-osx.yml'])
        subprocess.check_call(['bin/gsign', '-p', args.sign_prog, '--signer', args.signer, '--release', args.version+'-osx', '--destination', '../sigs/', 'inputs/sumokoin/contrib/gitian/gitian-osx.yml'])
        subprocess.check_call('mv build/out/sumokoin*.tar.bz2 ../out/'+args.version, shell=True)

    os.chdir(workdir)

    if args.commit_files:
        print('\nCommitting '+args.version+' Unsigned Sigs\n')
        os.chdir('sigs')
        subprocess.check_call(['git', 'add', args.version+'-linux/'+args.signer])
        subprocess.check_call(['git', 'add', args.version+'-android/'+args.signer])
        subprocess.check_call(['git', 'add', args.version+'-win/'+args.signer])
        subprocess.check_call(['git', 'add', args.version+'-osx/'+args.signer])
        subprocess.check_call(['git', 'commit', '-m', 'Add '+args.version+' unsigned sigs for '+args.signer])
        os.chdir(workdir)


def build():
    global args, workdir

    print('\nChecking Depends Freshness\n')
    os.chdir('builder')
    os.makedirs('inputs', exist_ok=True)

    subprocess.check_call(['wget', '-N', '-P', 'inputs', 'https://downloads.sourceforge.net/project/osslsigncode/osslsigncode/osslsigncode-1.7.1.tar.gz'])
    subprocess.check_call(['wget', '-N', '-P', 'inputs', 'https://bitcoincore.org/cfields/osslsigncode-Backports-to-1.7.1.patch'])
    subprocess.check_output(["echo 'a8c4e9cafba922f89de0df1f2152e7be286aba73f78505169bc351a7938dd911 inputs/osslsigncode-Backports-to-1.7.1.patch' | sha256sum -c"], shell=True)
    subprocess.check_output(["echo 'f9a8cdb38b9c309326764ebc937cba1523a3a751a7ab05df3ecc99d18ae466c9 inputs/osslsigncode-1.7.1.tar.gz' | sha256sum -c"], shell=True)
    subprocess.check_call(['make', '-C', 'inputs/sumokoin/contrib/depends', 'download', 'SOURCES_PATH=' + os.getcwd() + '/cache/common'])

    rebuild()


def verify():
    global args, workdir
    os.chdir('builder')

    print('\nVerifying v'+args.version+' Linux\n')
    subprocess.check_call(['bin/gverify', '-v', '-d', '../sigs/', '-r', args.version+'-linux', 'inputs/sumokoin/contrib/gitian/gitian-linux.yml'])
    print('\nVerifying v'+args.version+' Android\n')
    subprocess.check_call(['bin/gverify', '-v', '-d', '../sigs/', '-r', args.version+'-android', 'inputs/sumokoin/contrib/gitian/gitian-android.yml'])
    print('\nVerifying v'+args.version+' Windows\n')
    subprocess.check_call(['bin/gverify', '-v', '-d', '../sigs/', '-r', args.version+'-win', 'inputs/sumokoin/contrib/gitian/gitian-win.yml'])
    print('\nVerifying v'+args.version+' MacOS\n')
    subprocess.check_call(['bin/gverify', '-v', '-d', '../sigs/', '-r', args.version+'-osx', 'inputs/sumokoin/contrib/gitian/gitian-osx.yml'])
    os.chdir(workdir)

def main():
    global args, workdir

    parser = argparse.ArgumentParser(description='Script for running full Gitian builds.', usage='%(prog)s [options] signer version')
    parser.add_argument('-c', '--commit', action='store_true', dest='commit', help='Indicate that the version argument is for a commit or branch')
    parser.add_argument('-p', '--pull', action='store_true', dest='pull', help='Indicate that the version argument is the number of a github repository pull request')
    parser.add_argument('-u', '--url', dest='url', default='https://github.com/sumoprojects/sumokoin', help='Specify the URL of the repository. Default is %(default)s')
    parser.add_argument('-v', '--verify', action='store_true', dest='verify', help='Verify the Gitian build')
    parser.add_argument('-b', '--build', action='store_true', dest='build', help='Do a Gitian build')
    parser.add_argument('-B', '--buildsign', action='store_true', dest='buildsign', help='Build both signed and unsigned binaries')
    parser.add_argument('-o', '--os', dest='os', default='lawm', help='Specify which Operating Systems the build is for. Default is %(default)s. l for Linux, a for Android, w for Windows, m for MacOS')
    parser.add_argument('-r', '--rebuild', action='store_true', dest='rebuild', help='Redo a Gitian build')
    parser.add_argument('-R', '--rebuildsign', action='store_true', dest='rebuildsign', help='Redo and sign a Gitian build')
    parser.add_argument('-j', '--jobs', dest='jobs', default='2', help='Number of processes to use. Default %(default)s')
    parser.add_argument('-m', '--memory', dest='memory', default='2000', help='Memory to allocate in MiB. Default %(default)s')
    parser.add_argument('-k', '--kvm', action='store_true', dest='kvm', help='Use KVM instead of LXC')
    parser.add_argument('-d', '--docker', action='store_true', dest='docker', help='Use Docker instead of LXC')
    parser.add_argument('-S', '--setup', action='store_true', dest='setup', help='Set up the Gitian building environment. Uses LXC. If you want to use KVM, use the --kvm option. If you run this script on a non-debian based system, pass the --no-apt flag')
    parser.add_argument('-D', '--detach-sign', action='store_true', dest='detach_sign', help='Create the assert file for detached signing. Will not commit anything.')
    parser.add_argument('-n', '--no-commit', action='store_false', dest='commit_files', help='Do not commit anything to git')
    parser.add_argument('signer', nargs='?', help='GPG signer to sign each build assert file')
    parser.add_argument('version', nargs='?', help='Version number, commit, or branch to build.')
    parser.add_argument('-a', '--no-apt', action='store_true', dest='no_apt', help='Indicate that apt is not installed on the system')

    args = parser.parse_args()
    workdir = os.getcwd()

    args.linux = 'l' in args.os
    args.android = 'a' in args.os
    args.windows = 'w' in args.os
    args.macos = 'm' in args.os

    args.is_bionic = b'bionic' in subprocess.check_output(['lsb_release', '-cs'])

    if args.buildsign:
        args.build = True
        args.sign = True

    if args.rebuildsign:
        args.rebuild = True
        args.sign = True

    if args.kvm and args.docker:
        raise Exception('Error: cannot have both kvm and docker')

    args.sign_prog = 'true' if args.detach_sign else 'gpg --detach-sign'

    # Set enviroment variable USE_LXC or USE_DOCKER, let gitian-builder know that we use lxc or docker
    if args.docker:
        os.environ['USE_DOCKER'] = '1'
    elif not args.kvm:
        os.environ['USE_LXC'] = '1'
        if not 'GITIAN_HOST_IP' in os.environ.keys():
            os.environ['GITIAN_HOST_IP'] = '10.0.3.1'
        if not 'LXC_GUEST_IP' in os.environ.keys():
            os.environ['LXC_GUEST_IP'] = '10.0.3.5'

    # Disable MacOS build if no SDK found
    if args.macos and not os.path.isfile('builder/inputs/MacOSX10.11.sdk.tar.gz'):
        args.macos = False
        if args.build:
            print('Cannot build for MacOS, SDK does not exist. Will build for other OSes')

    script_name = os.path.basename(sys.argv[0])
    # Signer and version shouldn't be empty
    if args.signer == '':
        print(script_name+': Missing signer.')
        print('Try '+script_name+' --help for more information')
        sys.exit(1)
    if args.version == '':
        print(script_name+': Missing version.')
        print('Try '+script_name+' --help for more information')
        sys.exit(1)

    # Add leading 'v' for tags
    if args.commit and args.pull:
        raise Exception('Cannot have both commit and pull')
    args.commit = args.commit if args.commit else args.version

    if args.setup:
        setup()

    os.makedirs('builder/inputs/sumokoin', exist_ok=True)
    os.chdir('builder/inputs/sumokoin')
    if args.pull:
        subprocess.check_call(['git', 'fetch', args.url, 'refs/pull/'+args.version+'/merge'])
        args.commit = subprocess.check_output(['git', 'show', '-s', '--format=%H', 'FETCH_HEAD'], universal_newlines=True).strip()
        args.version = 'pull-' + args.version
    print(args.commit)
    subprocess.check_call(['git', 'fetch'])
    subprocess.check_call(['git', 'checkout', args.commit])
    os.chdir(workdir)

    if args.build:
        build()

    if args.rebuild:
        os.chdir('builder')
        rebuild()

    if args.verify:
        verify()

if __name__ == '__main__':
    main()
