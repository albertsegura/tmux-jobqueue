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

yes_answers = {'yes','y', '', 'si', 's'}
no_answers = {'no','n'}

parser = argparse.ArgumentParser(description = 'Mem trace analysis run folder')
parser.add_argument('session_name', action="store", help='');
parser.add_argument('run_file', action="store", help='');
args = parser.parse_args();

session_name = "job_"+os.path.relpath(args.session_name)+"_"+str(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
session_logname = session_name+".log"

if not os.path.isfile(args.run_file):
	print("Error: \""+args.run_file+"\" not a file")
	exit(-1)

print ("Session name:", session_name)
print ("Runfile:", args.run_file,"\n")
print ("Runfile content:")

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
print("Detected "+str(idx)+" jobs to run")
print ("")


# Ask for input
iscorrect = input("Is runfile content correct? [Y/n] ").lower()
if iscorrect not in yes_answers:
	exit(-1)

if os.environ.copy().get("TMUX") != None:
    insidetmux = input("Running inside TMUX, procede? [Y/n] ").lower()
    if insidetmux not in yes_answers:
        exit(-1)
    del os.environ['TMUX']


# Detect if session already exists
session_exists = True
try:
    cmd = ["tmux", "has-session", "-t", session_name]
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
except subprocess.CalledProcessError as e:
    session_exists = False

if session_exists:
    print("Error: session", session_name, "already exists")
    exit(-1)


# Launch job manager
try:
    tmux_cmds = "python3 ~/scripts/run_jobs_launcher.py "+session_name+" "+args.run_file
    tmux_cmds += " ; read"
    cmd = ["tmux", "new-session", "-d", "-s", session_name, tmux_cmds]
    output = subprocess.check_output(cmd)
except subprocess.CalledProcessError as e:
    print("Error: when launching",cmd)
    exit(-1)

print("Session launched")


# Ask to attach to new session
wantstoattach = input("Switch to tmux job session? [Y/n] ").lower()
if wantstoattach in yes_answers:
	cmd = ["tmux", "switch-client", "-t", session_name]
	# print(cmd)
	output = subprocess.check_output(cmd)
