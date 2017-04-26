import os


class Scheduler(object):
    """
    Class to represent a job on a scheduler like PBS, SLURM, or Local
    (for no scheduler). Maps conceptual names like 'nodes' to the specific
    command line arguments that need to be passed. Holds a reference to
    the corresponding runner (e.g. aprun or srun).

    It's job is to take a scheduler group and produce a script for executing
    all runs within the scheduler group with the indicated scheduler
    parameters.

    TODO: add another layer of abstraction that encapsulates templating
    and parameters for each scheduler, that could be used by other projects.
    This contains a lot of details specific to how we want to organize the
    output directories and keep track of the jobid and define run and monitor
    scripts, that is very specific to cheetah.
    """
    name = None # subclass must set
    submit_script_name = 'submit.sh'
    submit_out_name = 'codar.cheetah.submit-output.txt'
    run_out_name = 'codar.cheetah.run-output.txt'
    batch_script_name = None
    jobid_file_name = 'codar.cheetah.jobid.txt'

    def __init__(self, runner, output_directory):
        self.runner = runner
        self.output_directory = output_directory

    def write_submit_script(self):
        """
        Must at minimum produce a single script 'run.sh' within the
        output_directory that will run the batch in the background or submit
        the job to a real scheduler. Must also generate a file
        'codar.cheetah.jobid.txt' in the output directory that can be read by
        the monitor script to wait on the job (or process).
        """
        # subclass must implement
        raise NotImplemented()

    def write_batch_script(self, scheduler_group):
        """
        Must at minimum produce a single script 'run.sh' within the
        group_output_dir that will run the batch in the background or submit
        the job to a real scheduler. May also produce other auxiliary scripts,
        e.g. sbatch or pbs files. The 'run.sh' file must generate a file
        'codar.cheetah.jobid.txt' in the group output dir that can be read by
        the monitor script to wait on the job.
        """
        # subclass must implement
        raise NotImplemented()

    def read_jobid(self):
        jobid_file_path = os.path.join(self.output_directory,
                                       self.jobid_file_name)
        with open(jobid_file_path) as f:
            jobid = f.read()
        return jobid

    def write_monitor_script(self):
        """Must at minimum produce a script 'monitor.sh' which will monitor the
        progress of the job after 'run.sh' produced by `write_batch_script`
        is run. The 'run.sh' script will run the experiment batch in the
        background, and this script will monitor it's progress and optionally
        trigger actions, such as sending an email or running result
        analysis."""
        # subclass must implement
        raise NotImplemented()


class SchedulerLocal(Scheduler):
    """
    Batch type that ignores all scheduler options and runs the command directly
    on the local machine with bash, one at a time with no parallelism.

    An instance ties the scheduler together with a specific runner. Some
    schedulers may require a certain type of runner, but others may support
    multiple runners.
    """
    name = 'local'
    batch_script_name = 'local-run.sh'

    SUBMIT_TEMPLATE = """#!/bin/bash

cd {group_directory}
nohup {batch_script_name} >{submit_out_name} 2>&1 &
PID=$!
echo "{name}:$PID" > {jobid_file_name}
"""

    BATCH_HEADER = """#!/bin/bash

set -x
set -e

"""

    def write_submit_script(self):
        submit_path = os.path.join(self.output_directory,
                                   self.submit_script_name)
        with open(submit_path, 'w') as f:
            body = self.SUBMIT_TEMPLATE.format(
                        group_directory=self.output_directory,
                        batch_script_name=self.batch_script_name,
                        submit_out_name=self.submit_out_name,
                        jobid_file_name=self.jobid_file_name,
                        name=self.name)
            f.write(body)
        return submit_path

    def write_batch_script(self, exe, scheduler_group):
        script_path = os.path.join(self.output_directory,
                                   self.batch_script_name)
        with open(script_path, 'w') as f:
            # ignore all scheduler parameters for local runs, and just
            # use a fixed hearder
            f.write(self.BATCH_HEADER)
            for i, run in enumerate(scheduler_group.get_runs(
                                        exe, self.output_directory)):
                command_dir = 'run-%03d' % (i+1)
                lines = self.runner.wrap_app_command(command_dir,
                                                     self.run_out_name,
                                                     run)
                if lines:
                    f.write('\n'.join(lines))
                    f.write('\n')
        return script_path


class SchedulerPBS(Scheduler):
    # TODO: this is broken, just copied and started refactor from pbs
    # module
    name = 'local'
    batch_script_name = 'job.pbs'

    supported_params = ['name', 'project', 'nodes', 'walltime']

    HEADER_TEMPLATE = """#!/bin/bash
#PBS -N {name}
#PBS -A {project}
#PBS -l nodes={nodes}
#PBS -l walltime={walltime}

    """

    # The standard strategy for getting scheduler output files to appear in
    # a certain directory are to cd to that directory before running qsub.
    SUBMIT_TEMPLATE = """#!/bin/bash

cd "{scheduler_directory}"
qsub {batch_script_name}
"""

    def write_batch_script(self, group):
        """
        Open and write a PBS file to the specified path and return the open file
        object for further writing. Caller is responsible for closing the file.

        TODO: rather than passing back a file, this should probably return
        an object with an 'add_run' function. There should also be a template
        for the run output dir set somewhere - maybe other modules handle that,
        it should not be scheduler specific.
        """
        pbs_path = os.path.join(scheduler_dir_path, PBS_NAME)
        f = open(pbs_path, "w")
        f.write(PBS_FORMAT_TEMPLATE.format(name=name, project=project,
                                           nodes=nodes, walltime=walltime))
        return f


    def write_submit_script(self, script_out_path, scheduler_dir_path):
        """
        Write a bash script that will submit a PBS file generated by
        `open_pbs_file` with the correct working directory and enironment.
        This is the end user (experiment runner)'s entry point to start the
        experiment.
        """
        with open(script_out_path, 'w') as f:
            f.write(SUBMIT_FORMAT_TEMPLATE.format(
                        scheduler_directory=scheduler_dir_path,
                        pbs_name=PBS_NAME))
