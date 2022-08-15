#!/bin/bash
#
# CEC Client script.
# Used to send commands to a running CEC Daemon (cecd).
# CEC Daemon will be started automatically in background if necessary.
#

# Script variables
SCRIPT_DIR=`dirname "$0"`
ACTION="$1"
CEC_DAEMON="$SCRIPT_DIR/cecd.sh"
CEC_IN="$SCRIPT_DIR/cecd.in"
CEC_STATUS="$SCRIPT_DIR/cecd.status"

# Check args
if [ -z "$ACTION" ]; then  
	echo "Usage: $0 <on|off|status>"
	exit 0
fi

# Check if daemon is running and start it if necessary
if ! "$CEC_DAEMON" status >/dev/null; then
	"$CEC_DAEMON" start
	sleep 1
fi

# Check action
RET=0
case "$ACTION" in
	on)
		echo "on" > "$CEC_IN"
		RET=$?
		;;
	off)
		echo "off" > "$CEC_IN"
		RET=$?
		;;
	status)
		[ -e "$CEC_STATUS" ] && cat "$CEC_STATUS" || echo "0"
		;;
	*)
		echo "Usage: $0 <on|off|status>"
		;;
esac

exit $RET
