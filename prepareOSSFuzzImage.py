import argparse
import os
import time

import docker
from ipdb import launch_ipdb_on_exception

import cfgs

import logging
logger = logging.getLogger(__name__)

def validate_target_cfg(target):
    tdir = '%s/%s' % (cfgs.FDGPT_OSSFUZZ_TARGETS, target)
    tcfg = '%s/cfg.yml' % (tdir)
    tbuildsh = '%s/fuzzdrivergpt_build.sh' % (tdir)
    if (not os.path.exists(tcfg)) or (not os.path.exists(tbuildsh)):
        raise Exception('%s has missing cfg files (%s or %s does not exist)' % (target, tcfg, tbuildsh))

def get_fuzzdrivergpt_imgname(target):
    # Handle special cases for JS and Python targets
    if target.endswith('-js'):
        return 'fuzzdrivergpt-jsfuzz:latest'
    elif target.endswith('-py'):
        return 'fuzzdrivergpt-pythonfuzz:latest'
    return 'fuzzdrivergpt/%s:env' % (target)

def get_vanilla_ossfuzz_imgname(target):
    return 'fuzzdrivergpt/%s:vanilla-ossfuzz' % (target)

def get_base_imgname(target):
    # For JS/Python targets, use the appropriate base image
    if target.endswith('-js'):
        return 'ubuntu:20.04'  # Base for jsfuzz
    elif target.endswith('-py'):
        return 'ubuntu:20.04'  # Base for pythonfuzz
    return 'gcr.io/oss-fuzz/%s:latest' % (target)

def get_image(client, imgname, retries=3, delay=1):
    img = None
    for attempt in range(retries):
        try:
            img = client.images.get(imgname)
            break
        except docker.errors.ImageNotFound as ex:
            img = None
            if attempt < retries - 1:
                logger.warning('Image %s not found, retrying in %s seconds...' % (imgname, delay))
                time.sleep(delay)
            else:
                logger.error('Image %s not found after %s attempts' % (imgname, retries))
    return img

def is_fuzzdrivergpt_image_exist(target):
    client = docker.from_env()
    imgname = get_fuzzdrivergpt_imgname(target)
    img = get_image(client, imgname)

    return img != None

def build_image(client, target, imgname, volumes, command, message):
    baseimgname = get_base_imgname(target)
    repo, tag = imgname.split(':')

    # Determine language based on target name
    lang = 'c'  # default
    if target.endswith('-js'):
        lang = 'javascript'
    elif target.endswith('-py'):
        lang = 'python'

    env = [
        'FUZZING_ENGINE=libfuzzer',
        'SANITIZER=address',
        'ARCHITECTURE=x86_64',
        'PROJECT_NAME=%s' % (target),
        'HELPER=True',
        'FUZZING_LANGUAGE=%s' % lang,
    ]

    # Special handling for JS/Python targets
    if target.endswith('-js') or target.endswith('-py'):
        # For JS/Python we build directly from Dockerfile
        try:
            logger.info("Building image %s using dockerfile..." % imgname)
            client.images.build(
                path=os.path.join(cfgs.FDGPT_ROOT),
                dockerfile=command.split(' -f ')[1].split(' ')[0],
                tag=imgname,
                platform='linux/amd64',
                buildargs={'FUZZING_LANGUAGE': lang}
            )
        except docker.errors.BuildError as e:
            logger.error("Failed to build image: %s" % str(e))
            raise e
        return

    # For other targets, use container run + commit approach
    d = client.containers.run(baseimgname, command=command, volumes=volumes, environment=env,
                          platform='amd64', shm_size='2g', remove=False, privileged=True, detach=True)
    logger.debug(d.short_id)
    d.reload()
    ret = d.wait()
    if ret['Error'] != None or ret['StatusCode'] != 0:
        raise Exception('container %s of target %s has abnormal return status %s' % (d.id, target, ret))
    # commit the container
    d.reload()
    d.commit(repository=repo, tag=tag, author='fuzzdrivergpt', message=message)
    d.remove(force=True)

def build_fuzzdrivergpt_env_image(client, target):
    imgname = get_fuzzdrivergpt_imgname(target)
    
    # Special handling for JS/Python targets
    if target.endswith('-js'):
        dockerfile = os.path.join(cfgs.FDGPT_ROOT, 'dockerized-fuzzers/jsfuzz-docker')
        command = 'docker build -t %s -f %s .' % (imgname, dockerfile)
    elif target.endswith('-py'):
        dockerfile = os.path.join(cfgs.FDGPT_ROOT, 'dockerized-fuzzers/pythonfuzz-dockerfile')
        command = 'docker build -t %s -f %s .' % (imgname, dockerfile)
    else:
        command = 'bash /root/workspace/fuzzdrivergpt/ossfuzz-targets/%s/fuzzdrivergpt_build.sh' % (target)
    
    message = 'fuzzdrivergpt env has been created.'
    volumes = []
    
    if not target.endswith('-js') and not target.endswith('-py'):
        volumes.append('%s/%s:/root/workspace/fuzzdrivergpt/ossfuzz-targets/%s' % (cfgs.FDGPT_OSSFUZZ_TARGETS, target, target))
    
    build_image(client, target, imgname, volumes, command, message)

def build_vanilla_ossfuzz_image(client, target):
    # Skip for JS/Python targets as they don't use OSS-Fuzz base images
    if target.endswith('-js') or target.endswith('-py'):
        logger.info('Skipping vanilla OSS-Fuzz image build for %s - not required for JS/Python targets' % target)
        return
        
    imgname = get_vanilla_ossfuzz_imgname(target)
    command = 'compile'
    message = 'Vanilla ossfuzz env has been created.'
    volumes = []
    build_image(client, target, imgname, volumes, command, message)

def main():
    # parse args
    parser = argparse.ArgumentParser(description='Build the image of target project for fuzzdrivergpt, by default the image name is fuzzdrivergpt/xxx:env')
    parser.add_argument('-f', '--force', action='store_true', required=False, default=False, help='remove the image first if it exists and rebuild')
    parser.add_argument('-t', '--imagetype', required=True, choices=[ 'fuzzdrivergpt-env', 'vanilla-ossfuzz' ], help='set the type of the target image that needs to be built')
    parser.add_argument('targets', nargs='+', help='target project names e.g., jsonnet/libaom/... ALL means all')
    args = parser.parse_args()

    targets = args.targets
    force = args.force
    imgtype = args.imagetype

    client = docker.from_env()

    if imgtype == 'fuzzdrivergpt-env':
        # Skip config validation for JS/Python targets
        for target in targets:
            if not target.endswith('-js') and not target.endswith('-py'):
                validate_target_cfg(target)

        # check img setting exsits
        inlist_targets = []
        for target in targets:
            imgname = get_fuzzdrivergpt_imgname(target)

            img = get_image(client, imgname)
            if img != None:
                if not force:
                    # exist, not force, we skip the build
                    logger.info('=== skipping %s as image %s exists ===' % (target, imgname))
                    continue
                else:
                    # exist & force, we remove the img
                    logger.info('=== force mode, removing %s existing image %s ===' % (target, imgname))
                    client.images.remove(img.id)

            baseimgname = get_base_imgname(target)
            baseimg = get_image(client, baseimgname)
            if baseimg == None:
                raise Exception('%s is failed to be built since its base image does not exist: %s' % (target, baseimgname))

            inlist_targets.append(target)
    
        # for targets in list, build their images
        for target in inlist_targets:
            imgname = get_fuzzdrivergpt_imgname(target)
            logger.info('=== building image of %s -- %s ===' % (target, imgname))
            build_fuzzdrivergpt_env_image(client, target)

    elif imgtype == 'vanilla-ossfuzz':
        # check img setting exsits
        inlist_targets = []
        for target in targets:
            imgname = get_vanilla_ossfuzz_imgname(target)

            img = get_image(client, imgname)
            if img != None:
                if not force:
                    # exist, not force, we skip the build
                    logger.info('=== skipping %s as image %s exists ===' % (target, imgname))
                    continue
                else:
                    # exist & force, we remove the img
                    logger.info('=== force mode, removing %s existing image %s ===' % (target, imgname))
                    client.images.remove(img.id)

            baseimgname = get_base_imgname(target)
            baseimg = get_image(client, baseimgname)
            if baseimg == None:
                raise Exception('%s is failed to be built since its base image does not exist: %s' % (target, baseimgname))

            inlist_targets.append(target)
    
        # for targets in list, build their images
        for target in inlist_targets:
            imgname = get_vanilla_ossfuzz_imgname(target)
            logger.info('=== building image of %s -- %s ===' % (target, imgname))
            build_vanilla_ossfuzz_image(client, target)

if __name__ == '__main__':
    with launch_ipdb_on_exception():
        main()
    #main()
