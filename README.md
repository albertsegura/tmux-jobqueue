# tmux-jobqueue

Simple and dirty job queue manager for TMUX 

Takes as input a new TMUX session name, and a run_file containing all comands to execute.


To run:
```sh
python3 run_jobs.py session_name run_file
```

It creates a tmux session with one window for the job launcher and a window for monitoring the return value of the jobs.
Afterwards, creates a window for each of the comands listed in a run_file.
It only allows 4 simultaneously running processes (hardcoded, easy to change).
