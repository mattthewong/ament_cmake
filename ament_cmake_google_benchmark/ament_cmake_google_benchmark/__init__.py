# Copyright 2020 Open Source Robotics Foundation, Inc.
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

import argparse
import json
import subprocess
import sys


extra_metric_exclusions = {
  'name',
  'run_name',
  'run_type',
  'repetitions',
  'repetition_index',
  'threads',
  'iterations',
  'real_time',
  'cpu_time',
  'time_unit',
  }


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description='Run a Google Benchmark test and convert the results to '
                    'a common format.')
    parser.add_argument(
        'result_file_in', help='The path to the Google Benchmark result file')
    parser.add_argument(
        'result_file_out',
        help='The path to where the common result file should be written')
    parser.add_argument(
        '--package-name',
        help="The package name to be used as a prefix for the 'group' "
             'value in benchmark result files')
    parser.add_argument(
        '--command',
        nargs='+',
        help='The test command to execute. '
             'It must be passed after other arguments since it collects all '
             'following options.')
    if '--command' in argv:
        index = argv.index('--command')
        argv, command = argv[0:index + 1] + ['dummy'], argv[index + 1:]
    args = parser.parse_args(argv)
    args.command = command

    res = subprocess.run(args.command)

    try:
        with open(args.result_file_in, 'r') as in_file:
            with open(args.result_file_out, 'w') as out_file:
                convert_google_benchark_to_jenkins_benchmark(in_file, out_file, args.package_name)
    except FileNotFoundError:
        if res.returncode == 0:
            print(
                'ERROR: No performance test results were found at: %s' % args.result_file_in,
                file=sys.stderr)
            res.returncode = 1

    return res.returncode


def convert_google_benchark_to_jenkins_benchmark(in_file, out_file, package_name):
    in_data = json.load(in_file)
    out_data = {
        'groups': [
            {
                'name': package_name,
                'tests': [],
            },
        ],
    }
    for benchmark in in_data.get('benchmarks', []):
        out_data['groups'][0]['tests'].append({
            'name': benchmark['name'],
            'parameters': [
                {
                    'name': 'iterations',
                    'value': benchmark['iterations'],
                },
            ],
            'results': [
                {
                    'name': 'cpu_time',
                    'dblValue': benchmark['cpu_time'],
                    'unit': benchmark['time_unit'],
                },
                {
                    'name': 'real_time',
                    'dblValue': benchmark['real_time'],
                    'unit': benchmark['time_unit'],
                },
            ] + [
                {
                    'name': extra_name,
                    'value': benchmark[extra_name],
                } for extra_name in set(benchmark.keys()) - extra_metric_exclusions
            ],
        })
    else:
        print(
            'WARNING: The perfromance test results file contained no results',
            file=sys.stderr)

    json.dump(out_data, out_file)
