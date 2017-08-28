#!/bin/bash

cd "$(dirname $0)"/..
SRC_DIR=$(pwd)
OUT_DIR="$SRC_DIR"/test_output/local_scripts
RUN_DIR="$OUT_DIR"/group/run

mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR"/*
mkdir -p "$RUN_DIR"

# Copy local experiment scripts to output directory
cp -R "$SRC_DIR"/scripts/local/* "$OUT_DIR"

# Set up a fake environment for the campaign and group
cat >"$OUT_DIR"/campaign-env.sh <<EOF
export CODAR_CHEETAH_EXPERIMENT_DIR="$OUT_DIR"
export CODAR_CHEETAH_MACHINE_CONFIG=""
export CODAR_WORKFLOW_SCRIPT="$SRC_DIR/workflow.py"
export CODAR_WORKFLOW_RUNNER="none"
export CODAR_CHEETAH_WORKFLOW_LOG_LEVEL="DEBUG"
EOF

# Set up a fake environment for the experiment
cat >"$OUT_DIR"/group/group-env.sh <<EOF
export CODAR_CHEETAH_GROUP_WALLTIME="10"
export CODAR_CHEETAH_GROUP_MAX_PROCS="2"
EOF


# Create synthetic fobs
cat >"$OUT_DIR"/group/fobs.json <<EOF
[{ "name": "echo1", "exe": "/usr/bin/echo", "args": ["one"], "nprocs": 1, "working_dir": "$RUN_DIR"}, { "name": "echo2", "exe": "/usr/bin/echo", "args": ["two"], "nprocs": 1, "working_dir": "$RUN_DIR"}]
EOF

# Run
"$OUT_DIR"/run-all.sh
