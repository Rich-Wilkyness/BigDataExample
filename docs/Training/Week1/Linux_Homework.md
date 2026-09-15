# Homework Assignment: Linux Users, Permissions, Text Processing & Processes

## Objective

Practice the Linux commands covered in class, including user management, file permissions, `grep`, `awk`, `sed`, shell scripting, process management, and `systemctl`.

Complete each exercise from the Linux terminal. **For each exercise, submit the commands you used and the resulting terminal output.**

> **Note:** The outputs below are examples. Replace system-specific values such as IDs, dates, PIDs, memory, and service logs with your actual terminal output.

## Exercise 1: Create and manage a user

Create a new Linux user named `data_student`. Verify that the user exists using an appropriate command. Create a group named `data_team` and add `data_student` to that group. Display the user's UID, GID, and group memberships.

### Commands

```bash
# create the user and group, then add the user to the group data_student
# we could have created the group first and then used this command to add the user to it
# users don't need a group to function
sudo useradd -m data_student
# check if the user was created successfully
getent passwd data_student
# check if group exists
getent group
# check if the group was created successfully
sudo groupadd data_team
# check if the user was added to the group successfully
sudo usermod -aG data_team data_student
# verify the user's group memberships
id data_student

### Output

```text
uid=1001(data_student) gid=1001(data_student) groups=1001(data_student),1002(data_team)
```

### Explanation

`useradd -m` created the user and a home directory. `groupadd` created `data_team`, and `usermod -aG` added the user without removing existing group memberships. `-a` means append.

## Exercise 2: Practice file permissions

Create a file named `confidential.txt` containing at least one line of text. Change its permissions so that the owner can read and write it, the group can only read it, and everyone else has no permissions. Display the resulting permissions with `ls -l`. Do this using **numeric `chmod` notation**.

### Commands

```bash
echo "Private information" > confidential.txt
chmod 644 confidential.txt
ls -l confidential.txt
```

### Output

```text
-rw-r--r-- 1 root root 13 Sep 14 18:04 confidential.txt
```

### Explanation

The numeric mode `644` gives the owner read and write permissions, the group read permission, and everyone else read permission.

## Exercise 3: Practice symbolic `chmod`

Create a shell script named `hello.sh` that prints `Hello from Linux!`. Attempt to execute it before giving it execute permission. Then use symbolic `chmod` notation to give the owner execute permission and successfully run the script.

### Commands

```bash
nano hello.sh
chmod u+x hello.sh
./hello.sh
```

#!/bin/bash
echo Hello from Linux!


### Output

```text
bash: ./hello.sh: Permission denied
Hello from Linux!
```

### Explanation

The first execution failed because the file lacked execute permission. `chmod u+x` added execute permission for the owner, allowing the script to run.

## Exercise 4: Search data with `grep`

Create a file called `application.log` containing at least 10 lines. At least three lines should contain `ERROR`, two should contain `WARNING`, and the others should contain `INFO`. Use `grep` to:

- Find all `ERROR` lines.
- Find both `ERROR` and `WARNING` lines using one command.
- Count the number of lines containing `ERROR`.

### Commands

```bash
printf '%s\n' \
  "INFO Application started" \
  "INFO Database connected" \
  "ERROR Login failed" \
  "WARNING Disk space low" \
  "INFO Request received" \
  "ERROR Connection timed out" \
  "INFO Request completed" \
  "WARNING High memory use" \
  "ERROR File not found" \
  "INFO Application stopped" > application.log
grep 'ERROR' application.log
grep -E 'ERROR|WARNING' application.log
grep -c 'ERROR' application.log
```

### Output

```text
ERROR Login failed
ERROR Connection timed out
ERROR File not found

ERROR Login failed
WARNING Disk space low
ERROR Connection timed out
WARNING High memory use
ERROR File not found

3
```

### Explanation

`grep` found lines containing `ERROR`. The `-E` option allowed an OR expression, and `-c` returned the number of matching lines.

## Exercise 5: Process CSV data with `awk`

Create `employees.csv` with this structure and at least six employees:

```text
id,name,department,salary
1,Alice,Engineering,95000
2,Bob,Sales,72000
```

Use `awk` to display only employee names and salaries. Then use another `awk` command to display only employees earning more than `$80,000`.

### Commands

```bash
printf '%s\n' \
  'id,name,department,salary' \
  '1,Alice,Engineering,95000' \
  '2,Bob,Sales,72000' \
  '3,Carol,Engineering,88000' \
  '4,David,Marketing,68000' \
  '5,Eva,Finance,83000' \
  '6,Frank,Support,61000' > employees.csv
awk -F, 'NR > 1 {print $2, $4}' employees.csv
awk -F, 'NR > 1 && $4 > 80000 {print $2, $4}' employees.csv
```

### Output

```text
Alice 95000
Bob 72000
Carol 88000
David 68000
Eva 83000
Frank 61000

Alice 95000
Carol 88000
Eva 83000
```

### Explanation

`-F,` told `awk` that commas separate the fields. `NR > 1` skipped the header, while `$4 > 80000` selected employees whose salary exceeded `$80,000`.

## Exercise 6: Transform data with `sed`

Using your `employees.csv` file, use `sed` to replace every occurrence of `Engineering` with `Technology`. First display the transformed data **without changing the original file**. Then create a backup and use `sed` to make the change in the actual file.

### Commands

```bash
sed 's/Engineering/Technology/g' employees.csv
sed -i.bak 's/Engineering/Technology/g' employees.csv
ls -l employees.csv employees.csv.bak
```

### Output

```text
id,name,department,salary
1,Alice,Technology,95000
2,Bob,Sales,72000
3,Carol,Technology,88000
4,David,Marketing,68000
5,Eva,Finance,83000
6,Frank,Support,61000

-rw-r--r-- 1 student student 176 Sep 14 12:10 employees.csv
-rw-r--r-- 1 student student 178 Sep 14 12:10 employees.csv.bak
```

### Explanation

The first `sed` command displayed replacements without changing the file. The `-i.bak` option edited the file in place and saved the original as `employees.csv.bak`.

## Exercise 7: Create a system-information shell script

Create a script named `system_report.sh` that prints:

- Current username
- Current date and time
- Current working directory
- Available disk space
- Memory usage
- System uptime

Give the script appropriate execute permissions and run it using:

```bash
./system_report.sh
```

### Commands

```bash
printf '%s\n' \
  '#!/bin/bash' \
  'echo "Username: $(whoami)"' \
  'echo "Date: $(date)"' \
  'echo "Directory: $(pwd)"' \
  'echo "Disk space:"' \
  'df -h /' \
  'echo "Memory usage:"' \
  'free -h' \
  'echo "Uptime: $(uptime -p)"' > system_report.sh
chmod u+x system_report.sh
./system_report.sh
```

### Output

```text
Username: student
Date: Sun Sep 14 12:15:00 MDT 2026
Directory: /home/student
Disk space:
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        50G   12G   36G  25% /
Memory usage:
               total        used        free      shared  buff/cache   available
Mem:            7.7Gi       2.1Gi       3.8Gi       200Mi       1.8Gi       5.2Gi
Uptime: up 2 hours, 15 minutes
```

### Explanation

The script combined standard Linux commands to report user and system details. `chmod u+x` made the script executable by its owner.

## Exercise 8: Investigate running processes

Start the following process in the background:

```bash
sleep 500 &
```

Find its PID using `ps` or `pgrep`. Verify that it is running, terminate it using `kill`, and then demonstrate that the process no longer exists.

### Commands

```bash
sleep 500 &
sleep_pid=$!
echo "$sleep_pid"
ps -p "$sleep_pid"
kill "$sleep_pid"
ps -p "$sleep_pid"
```

### Output

```text
[1] 2450
2450
    PID TTY          TIME CMD
   2450 pts/0    00:00:00 sleep
[1]+  Terminated              sleep 500
    PID TTY          TIME CMD
```

### Explanation

`$!` stored the PID of the most recent background process. `ps` verified it was running, and `kill` terminated it; the final `ps` output showed it no longer existed.

## Exercise 9: Foreground and background jobs

Start:

```bash
sleep 1000
```

Suspend the process using the appropriate keyboard shortcut. Use `jobs` to display it, resume it in the background, use `jobs` again to verify its status, bring it back to the foreground, and finally terminate it.

### Commands

```text
sleep 1000
Ctrl+Z
jobs
bg %1
jobs
fg %1
Ctrl+C
```

### Output

```text
^Z
[1]+  Stopped                 sleep 1000
[1]+  Running                 sleep 1000 &
sleep 1000
^C
```

### Explanation

`Ctrl+Z` suspended the foreground job. `bg` resumed it in the background, `fg` brought it back to the foreground, and `Ctrl+C` terminated it.

## Exercise 10: Investigate a system service

Choose an existing systemd service on your machine, such as `ssh`, `cron`, or `docker`. Use `systemctl` to determine:

- Whether the service is running.
- Whether it is enabled at boot.
- The service's main PID, if running.

Then use `journalctl` to display the most recent 10 log entries for that service.

**Do not disable or permanently modify an important system service.**

### Commands

```bash
systemctl is-active cron
systemctl is-enabled cron
systemctl show cron --property=MainPID
sudo journalctl -u cron -n 10 --no-pager
```

### Output

```text
active
enabled
MainPID=742
Sep 14 12:00:01 linux CRON[2101]: Started scheduled task.
Sep 14 12:10:01 linux CRON[2150]: Started scheduled task.
(Additional recent entries omitted from this example.)
```

### Explanation

`systemctl` checked whether `cron` was running, enabled at boot, and identified its main PID. `journalctl` displayed the service's 10 most recent log entries without opening an interactive pager.

## Submission

Submit a single text or Markdown file named:

```text
linux_homework_<your_name>.txt
```

The goal is not simply to get the expected output. You should be able to explain **why each command worked and what its important options mean**.
