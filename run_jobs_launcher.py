#!/usr/bin/env python3

import sys
import argparse
import collections
import os
import math
import subprocess
import datetime
import re
import time
import signal
import tempfile
import fcntl

launcher_text = "\
                 _____                           _       _     \n\
                |_   _| __ ___  _   ___  __     | | ___ | |__  \n\
                  | || '_ ` _ \| | | \ \/ /  _  | |/ _ \| '_ \ \n\
                  | || | | | | | |_| |>  <  | |_| | (_) | |_) |\n\
                  |_||_| |_| |_|\__,_/_/\_\  \___/ \___/|_.__/ \n\
                                                               \n\
                  _                           _               \n\
                 | |    __ _ _   _ _ __   ___| |__   ___ _ __ \n\
                 | |   / _` | | | | '_ \ / __| '_ \ / _ \ '__|\n\
                 | |__| (_| | |_| | | | | (__| | | |  __/ |   \n\
                 |_____\__,_|\__,_|_| |_|\___|_| |_|\___|_|   \n"

monitor_text = "\
                 _____                           _       _     \n\
                |_   _| __ ___  _   ___  __     | | ___ | |__  \n\
                  | || '_ ` _ \| | | \ \/ /  _  | |/ _ \| '_ \ \n\
                  | || | | | | | |_| |>  <  | |_| | (_) | |_) |\n\
                  |_||_| |_| |_|\__,_/_/\_\  \___/ \___/|_.__/ \n\
                                                               \n\
                       __  __             _ _             \n\
                      |  \/  | ___  _ __ (_) |_ ___  _ __ \n\
                      | |\/| |/ _ \| '_ \| | __/ _ \| '__|\n\
                      | |  | | (_) | | | | | || (_) | |   \n\
                      |_|  |_|\___/|_| |_|_|\__\___/|_|   \n"



lock_a_file = tempfile.NamedTemporaryFile()
lock_b_file = tempfile.NamedTemporaryFile()
lock_c_file = tempfile.NamedTemporaryFile()
lock_a_fd = lock_a_file.fileno()
lock_b_fd = lock_b_file.fileno()
lock_c_fd = lock_c_file.fileno()

def handler_sigusr1(signum, frame):
	fcntl.flock(lock_c_fd, fcntl.LOCK_EX)
	global running_jobs, finished_jobs, total_jobs
	running_jobs -= 1
	finished_jobs += 1
	print(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+": ", end='')
	print("A job exited ("+str(finished_jobs)+"/"+str(total_jobs)+")")
	# print ("Signal handler1 called with signal", signum)
	fcntl.flock(lock_b_fd, fcntl.LOCK_UN)

def handler_sigusr2(signum, frame):
	# print ("Signal handler2 called with signal", signum)
	fcntl.flock(lock_b_fd, fcntl.LOCK_EX)
	fcntl.flock(lock_c_fd, fcntl.LOCK_UN)

parser = argparse.ArgumentParser(description = 'Mem trace analysis run folder')
parser.add_argument('session_name', action="store", help='');
parser.add_argument('run_file', action="store", help='');
args = parser.parse_args();

session_name = args.session_name
session_logname = session_name+".log"

# Output session information
print (launcher_text)
print ("Session name:", session_name)
print ("Runfile:", args.run_file)

runfile = open(args.run_file)
print ("========================================")
idx=0
for line in runfile:
    linecmd = line.rstrip('\n')
    if linecmd != "":
        print(str(idx)+": "+line,end='')
        idx += 1
runfile.close()
print ("========================================")
print(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+": ", end='')
print("Detected "+str(idx)+" jobs to run")
print ("")


# Create session logfile
session_logfile = open(session_logname,"w")
session_logfile.write(monitor_text+"\n")
session_logfile.write("Session name: "+session_name+"\n")
session_logfile.write("Runfile: "+args.run_file+"\n")
session_logfile.write("========================================\n")
runfile = open(args.run_file)
idx=0
for line in runfile:
	linecmd = line.rstrip('\n')
	if linecmd != "":
		session_logfile.write(str(idx)+": "+line)
		idx += 1
runfile.close()
session_logfile.write("========================================\n")
session_logfile.write("Detected "+str(idx)+" jobs to run\n")
session_logfile.write("Ctrl+C to exit, jobs will continue execution\n\n")
session_logfile.flush()


# Launch job monitor
cmd = ["tmux", "new-window", "-d", "-n", "monitor-log", "tail -n 80 -f "+session_logname]
# print(cmd)
output = subprocess.check_output(cmd)


# Launch jobs
jobs_cmd_line = []
runfile = open(args.run_file)
for line in runfile:
	line = line.rstrip('\n')
	if line != "":
		jobs_cmd_line.append(line)
runfile.close()

signal.signal(signal.SIGUSR1, handler_sigusr1)
signal.signal(signal.SIGUSR2, handler_sigusr2)
fcntl.flock(lock_b_fd, fcntl.LOCK_EX)

max_jobs_parallel = 4
launched_jobs = 0
running_jobs = 0
finished_jobs = 0
total_jobs = len(jobs_cmd_line)
while launched_jobs < total_jobs or (launched_jobs == total_jobs and running_jobs):
	if running_jobs < max_jobs_parallel and launched_jobs < total_jobs:
		line = jobs_cmd_line[launched_jobs]
		tmux_cmds = line+" ; "
		tmux_cmds += "exec 200> "+lock_a_file.name+" ; "
		tmux_cmds += "exec 201> "+lock_b_file.name+" ; "
		tmux_cmds += "exec 202> "+lock_c_file.name+" ; "
		tmux_cmds += "flock 200 ; "
		tmux_cmds += "echo \"Job: "+str(launched_jobs)+"  -  cmd: "+line+"\nReturn status: $?\n\" >> "+session_logname+" ; "
		tmux_cmds += "kill -SIGUSR1 "+str(os.getpid())+" ; "
		tmux_cmds += "flock 201 ; "
		tmux_cmds += "flock -u 201 ; "
		tmux_cmds += "kill -SIGUSR2 "+str(os.getpid())+" ; "
		tmux_cmds += "flock 202 ; "
		tmux_cmds += "flock -u 202 ; "
		tmux_cmds += "flock -u 200 ; "
		tmux_cmds += "read"
		cmd = ["tmux", "new-window", "-d", "-n", "Job_"+str(launched_jobs)+"_"+session_name, tmux_cmds]
		# print(cmd)
		output = subprocess.check_output(cmd)
		print(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+": ", end='')
		print("Job",launched_jobs,"of",total_jobs,"launched, waiting ...")
		time.sleep(0)
		launched_jobs += 1
		running_jobs += 1
	else:
		signal.pause()

signal.pause()

# Output finish message
session_logfile.write("All "+str(total_jobs)+" jobs launched, launcher exits\n\n")
session_logfile.close()
print(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+": ", end='')
print ("All", total_jobs, "jobs launched, launcher exits\n")

