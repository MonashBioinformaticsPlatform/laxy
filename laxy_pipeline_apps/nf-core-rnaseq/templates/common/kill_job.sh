#!/usr/bin/env bash
set -o nounset
set -o pipefail
# set -o xtrace

# We don't want to exit on error since we want to ultimately hit
# the curl HTTP request at the end, whether stuff fails or not
# set -o errexit

# These variables are overridden by environment vars if present
export DEBUG="${DEBUG:-{{ DEBUG }}}"
readonly JOB_PATH="${PWD}"
# readonly QUEUE_TYPE="{{ QUEUE_TYPE }}"

readonly LOCAL_JOB_PIDS="${JOB_PATH}/job.pids"
readonly SLURM_JOB_IDS="${JOB_PATH}/slurm.jids"

function kill_job() {
    IFS=$'\n'

    if [[ -f "${SLURM_JOB_IDS}" ]]; then
        for jid in $(cat "${SLURM_JOB_IDS}"); do
            scancel ${jid} || true
        done
    fi

    if [[ -f "${LOCAL_JOB_PIDS}" ]]; then
        for pid in $(cat "${LOCAL_JOB_PIDS}"); do
            kill ${pid} || true
        done
    fi
}

function check_job() {
    IFS=$'\n'

    if [[ -f "${SLURM_JOB_IDS}" ]]; then
        for jid in $(cat "${SLURM_JOB_IDS}"); do

            # TODO: Possibly deal with some of the more uncommon Slurm job state codes
            #       beyond R (RUNNING) and PD (PENDING).
            #       eg RD/RH/RQ/RS/SI/SO/ST/S etc (these may not be failure states)
            #       https://slurm.schedmd.com/squeue.html#lbAG
            state=$(squeue --noheader --jobs ${jid} --format %t)
            # squeue_exit_code=$?
            if [[ "${state}" == "R" ]] || [[ "${state}" == "PD" ]]; then
                echo "RUNNING"
                exit 0
            fi

            # This method requires SLURM accounting to be enabled - not always enabled by default
            # state=$(sacct --parsable2 --format=state --jobs ${jid} | tail -1)
            # if [[ "${state}" == "RUNNING" ]]; then
            #     echo "RUNNING"
            #     exit 0
            # fi
        done
    fi

    if [[ -f "${LOCAL_JOB_PIDS}" ]]; then
        for pid in $(cat "${LOCAL_JOB_PIDS}"); do
            # 0=running, 1=not found (finished)
            state=$(ps --pid ${pid} >/dev/null; echo $?)
            if [[ "${state}" == 0 ]]; then
                echo "RUNNING"
                exit 0
            fi
        done
    fi
    echo "NO JOBS/PROCESSES RUNNING"
    exit 1
}

function show_help() {
    echo "Usage: kill_job.sh <kill | check>"
    echo
    echo "Reads local PIDs and SLURM job IDs from the files ${LOCAL_JOB_PIDS} and ${SLURM_JOB_IDS}."
    echo
    echo "kill: Terminates all listed SLURM jobs and local processes (via scancel and kill)."
    echo "check: Returns zero exit code if some tasks are still running, non-zero if no tasks are running"

    exit 1
}

if [[ $# -gt 0 ]]; then
    if [[ $1 == 'kill' ]]; then
        kill_job
    elif [[ $1 == 'check' ]]; then
        check_job
    else
        show_help
    fi
else
    show_help
fi
