"""
Funtions to print status information for campaigns.
"""
import os
import json
from collections import defaultdict
import logging
import glob

from codar.cheetah.helpers import get_immediate_subdirs, \
                                  require_campaign_directory


def print_campaign_status(campaign_directory, filter_user=None,
                          filter_group=None, filter_run=None,
                          group_details=False,
                          print_logs=False, log_level='DEBUG',
                          return_codes=False, print_output=False):
    require_campaign_directory(campaign_directory)
    user_dirs = get_immediate_subdirs(campaign_directory)
    for user in user_dirs:
        if filter_user and user not in filter_user:
            continue
        user_dir = os.path.join(campaign_directory, user)
        group_dirs = get_immediate_subdirs(user_dir)
        for group in group_dirs:
            if filter_group and group not in filter_group:
                continue
            user_group = user + '/' + group
            group_dir = os.path.join(user_dir, group)
            jobid_file_path = os.path.join(group_dir,
                                           'codar.cheetah.jobid.txt')
            if not os.path.exists(jobid_file_path):
                print(user_group, ':', 'NOT SUBMITTED')
                continue

            with open(jobid_file_path) as f:
                jobid = f.read().strip()
                jobid = jobid.split(':')[1]

            log_file_path = os.path.join(group_dir, 'codar.FOBrun.log')
            status_file_path = os.path.join(group_dir,
                                            'codar.workflow.status.json')
            walltime_file_path = os.path.join(group_dir,
                                              'codar.cheetah.walltime.txt')
            if os.path.exists(status_file_path):
                status_data, state_counts, reason_counts, rc_counts = \
                                    get_workflow_status(status_file_path)
                total = len(status_data)
                if os.path.exists(walltime_file_path):
                    ok = reason_counts['succeeded']
                    if ok < total:
                        print(user_group, ':', 'DONE,',
                              total-ok, '/', total, 'failed')
                    else:
                        print(user_group, ':', 'DONE')
                else:
                    in_progress = (state_counts['running']
                                   + state_counts['not_started'])
                    print(user_group, ':', 'IN PROGRESS,', 'job', jobid,
                          ',', total-in_progress, '/', total)
                if group_details:
                    get_workflow_status(status_file_path, print_counts=True,
                                        indent=2)
                if return_codes:
                    get_workflow_status(status_file_path,
                                        print_return_codes=True, indent=2,
                                        filter_run=filter_run)
                if print_logs:
                    _print_fobrun_log(log_file_path, log_level, filter_run)
                if print_output:
                    _print_group_code_output(group_dir, filter_run)
            else:
                print(user_group, ':', 'NOT STARTED')


def _print_fobrun_log(log_file_path, log_level, filter_run=None):
    log_level_int = getattr(logging, log_level.upper(), None)
    if not isinstance(log_level_int, int):
        raise ValueError('Invalid log level: %s' % log_level)
    with open(log_file_path) as f:
        for line in f:
            line = line.strip()
            _, line_level, _ = _parse_fobrun_log_line(line)
            if line_level < log_level_int:
                continue
            if filter_run:
                found = False
                for fr in filter_run:
                    if fr in line:
                        found = True
                        break
                if not found:
                    continue
            print(' ', line)


def _print_group_code_output(group_dir, filter_run=None):
    run_dirs = get_immediate_subdirs(group_dir)
    for run_name in run_dirs:
        if filter_run and run_name not in filter_run:
            continue
        run_dir = os.path.join(group_dir, run_name)
        _print_run_code_output(run_name, run_dir)


def _print_run_code_output(run_name, run_dir):
    # Note: this also handles experiments using component subdirs, where
    # the files are in a subdirectory with the code's name
    out_files = (glob.glob(os.path.join(run_dir, 'codar.workflow.stdout.*'))
                +glob.glob(os.path.join(run_dir, '*/codar.workflow.stdout.*')))
    err_files = (glob.glob(os.path.join(run_dir, 'codar.workflow.stderr.*'))
                +glob.glob(os.path.join(run_dir, '*/codar.workflow.stderr.*')))

    outputs = defaultdict(dict) # key is code name, values are
                                # dict { 'out': '...', 'err': '...'}
    for fpath in out_files:
        fname = os.path.basename(fpath)
        parts = fname.split('.')
        code = parts[-1]
        outputs[code]['out'] = fpath
    for fpath in err_files:
        fname = os.path.basename(fpath)
        parts = fname.split('.')
        code = parts[-1]
        outputs[code]['err'] = fpath

    for code in sorted(outputs.keys()):
        for k in ['out', 'err']:
            if k not in outputs[code]:
                continue
            fpath = outputs[code][k]
            size = os.path.getsize(fpath)
            print('>>>', run_name, code, 'std' + k, '(%d bytes)' % size)
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    print(line)
            print()


def _parse_fobrun_log_line(line):
    dt_string = line[:24]
    level, message = line[24:].split(':', 1)
    level = _numeric_log_level(level)
    return dt_string, level, message


def _numeric_log_level(log_level_string):
    log_level_int = getattr(logging, log_level_string.upper(), None)
    if not isinstance(log_level_int, int):
        raise ValueError('Invalid log level: %s' % log_level_string)
    return log_level_int


def get_workflow_status(status_file_path, print_counts=False, indent=0,
                        print_return_codes=False, filter_run=None):
    with open(status_file_path) as f:
        status_data = json.load(f)

    total_count = len(status_data)
    total_rc = 0
    rc_counts = defaultdict(int)
    state_counts = dict(not_started=0, running=0, done=0, killed=0)
    total_reasons = 0
    reason_counts = defaultdict(int)

    for st in status_data.values():
        state_counts[st['state']] += 1
        reason = st.get('reason')
        if reason:
            reason_counts[reason] += 1
            total_reasons += 1
        return_codes = st.get('return_codes')
        if return_codes:
            for rc in return_codes.values():
                total_rc += 1
                rc_counts[rc] += 1

    prefix = " " * indent
    if print_counts:
        print('%s== total runs:' % prefix, total_count)
        for k in sorted(state_counts.keys()):
            v = state_counts[k]
            print('%sstate  %11s: %d' % (prefix, k, v))
        print('\n%s== total w/ reason:' % prefix, total_reasons)
        for k in sorted(reason_counts.keys()):
            v = reason_counts[k]
            print('%sreason %11s: %d' % (prefix, k, v))
        print('\n%s== total return codes:' % prefix, total_rc)
        for k in sorted(rc_counts.keys()):
            v = rc_counts[k]
            print('%sreturn code %d: %d' % (prefix, k, v))
        print()

    if print_return_codes:
        for run_name in sorted(status_data.keys()):
            if filter_run and run_name not in filter_run:
                continue
            run_data = status_data[run_name]
            rc = run_data.get('return_codes', {})
            if not rc:
                continue
            print(prefix + run_name)
            for code_name in sorted(rc.keys()):
                print('%s%s: %d'
                      % (prefix * 2, code_name, rc[code_name]))
        print()

    return status_data, state_counts, reason_counts, rc_counts
