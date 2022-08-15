#!/bin/bash
#
# CEC Daemon script.
# Used to run/start/stop/check the CEC Daemon (cecd) Python script.
#

# Script variables
SCRIPT_DIR=`dirname "$0"`
SCRIPT_NAME="cecd"
ACTION="$1"
CEC_DAEMON="$SCRIPT_DIR/$SCRIPT_NAME.py"
CEC_PID="$SCRIPT_DIR/$SCRIPT_NAME.pid"
CEC_IN="$SCRIPT_DIR/$SCRIPT_NAME.in"
CEC_OUT="$SCRIPT_DIR/$SCRIPT_NAME.out"
CEC_ERR="$SCRIPT_DIR/$SCRIPT_NAME.err"
CEC_STATUS="$SCRIPT_DIR/$SCRIPT_NAME.status"

# Create named pipe if necessary
[ -e "$CEC_IN" ] || mkfifo "$CEC_IN"

# Check daemon status (0=started, 1=stopped)
daemon_status() {
	local RET=1
	if [ -e "$CEC_PID" ]; then
		local PID=$(cat "$CEC_PID")
		if kill -0 "$PID" >/dev/null 2>&1; then
			RET=0
		else
			rm -f "$CEC_PID"
		fi
	fi
	return $RET
}

# Run daemon in the foreground
daemon_run() {
	$CEC_DAEMON --status "$CEC_STATUS" --pid "$CEC_PID"
}

# Start daemon in the background
daemon_start() {
	echo "Starting $SCRIPT_NAME ..."
	$CEC_DAEMON --input "$CEC_IN" --output "$CEC_OUT" --error "$CEC_ERR" --status "$CEC_STATUS" --pid "$CEC_PID" &
}

# Wait for daemon to exit if running
daemon_wait() {
	if [ -e "$CEC_PID" ]; then
		local PID=$(cat "$CEC_PID")
		echo "Waiting for shutdown ..."
		wait $PID
		rm -f "$CEC_PID"
	fi
}

# Kill daemon if running
daemon_stop() {
	if [ -e "$CEC_PID" ]; then
		local PID=$(cat "$CEC_PID")
		if kill -0 "$PID" >/dev/null 2>&1; then
			echo "Killing pid $PID"
			kill "$PID"
		fi
	fi
}

# Check action
RET=0
case "$ACTION" in
	run)
		if daemon_status; then
			echo "$SCRIPT_NAME is already running"
			RET=1
		elif ! daemon_run; then
			echo "$SCRIPT_NAME failed to start"
			RET=1
		fi
		;;
	start)
		if daemon_status; then
			echo "$SCRIPT_NAME is already running"
		elif daemon_start; then
			echo "$SCRIPT_NAME started"
		else
			echo "$SCRIPT_NAME failed to start"
			RET=1
		fi
		;;
	stop)
		if daemon_status; then
			daemon_stop
			echo "$SCRIPT_NAME stopped"
		else
			echo "$SCRIPT_NAME is not running"
		fi
		;;
	status)
		if daemon_status; then
			echo "$SCRIPT_NAME is running"
		else
			echo "$SCRIPT_NAME is stopped"
			RET=1
		fi
		;;
	*)
		echo "Usage: $0 <run|start|stop|status>"
		;;
esac

exit $RET
