# CEC Daemon & Client

Daemon and client scripts to control HDMI devices via the CEC protocol.

## Installation

Execute the following commands on a Debian or Ubuntu system to install the required dependencies:
```
apt-get update
apt-get install -y python3-cec
```

## Usage

### Server

Execute the following command to start the daemon:

```
./cecd.sh start
```

The following arguments are available:

```
./cecd.sh <run|start|stop|status>
```

### Client

Execute the following commands to interact with the daemon:

```
# Get TV status:
./cecc.sh status

# Power on TV:
./cecc.sh on

# Power off TV:
./cecc.sh off
```

Note: the client script will automatically start the daemon if it is not already running.
