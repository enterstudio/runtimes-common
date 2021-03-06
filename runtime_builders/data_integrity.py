#!/usr/bin/python

# Copyright 2017 Google Inc. All rights reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import glob
import json
import logging
import os
from ruamel import yaml
import shutil
import sys
import tempfile

import builder_util


def main():
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', '-d',
                        help='directory containing all builder config files',
                        required=True)
    args = parser.parse_args()

    return _verify(args.directory)


def _verify(directory):
    failures = 0

    try:
        for config_file in glob.glob(os.path.join(directory, '*.json')):
            with open(config_file, 'r') as f:
                config = json.load(f)
                project_name = config['project']
                latest_file = config['latest']
                failures += _verify_latest_files_match(project_name,
                                                       latest_file)
                failures += _verify_latest_file_exists(latest_file)
        return failures
    except ValueError as ve:
        logging.error('Error when parsing JSON! Check file formatting. \n{0}'
                      .format(ve))
    except KeyError as ke:
        logging.error('Config file is missing required field! \n{0}'
                      .format(ke))


def _verify_latest_files_match(project_name, config_latest):
    """
    Verify that the file pointed to by <project_name>.version is the same
    as the file specified in the builder config
    """
    remote_version = builder_util.RUNTIME_BUCKET_PREFIX + \
        project_name + '.version'
    try:
        tmpdir = tempfile.mkdtemp()
        version_file = os.path.join(tmpdir, 'runtime.version')
        builder_util._get_file_from_gcs(remote_version, version_file)

        with open(version_file, 'r') as f:
            version_contents = f.read().strip('\n').strip(' ')
            version_latest = builder_util.RUNTIME_BUCKET_PREFIX + \
                project_name + '-' + version_contents + '.yaml'
            if version_latest != config_latest:
                logging.error('Builders do not match!')
                logging.error('Latest builder in internal runtime config: '
                              '{0}'.format(config_latest))
                logging.error('Latest builder in runtime.version file: '
                              '{0}'.format(version_latest))
                return 1
        return 0
    finally:
        shutil.rmtree(tmpdir)


def _verify_latest_file_exists(latest_file_path):
    """
    Verify that the latest file pointed to by <project_name>.version
    exists and is valid yaml
    """
    try:
        logging.info('Checking file {0}'.format(latest_file_path))
        tmpdir = tempfile.mkdtemp()
        latest_file = os.path.join(tmpdir, 'latest.yaml')
        if not builder_util._get_file_from_gcs(latest_file_path, latest_file):
            logging.error('File {0} not found in GCS!'
                          .format(latest_file_path))
            return 1
        with open(latest_file, 'r') as f:
            yaml.round_trip_load(f)
        return 0
    except yaml.YAMLError as ye:
        logging.error(ye)
        return 1
    finally:
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    sys.exit(main())
