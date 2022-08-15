#!/usr/bin/python3

import argparse
import cec
import errno
import logging
import os
import signal
import stat
import sys

class CecDaemon:
  cecconfig = cec.libcec_configuration()
  device = cec.CECDEVICE_TV
  log_level = logging.DEBUG
  input_path = None
  output_file = sys.stdout
  error_file = sys.stderr
  status_path = None
  pid_path = None
  run_loop = True
  read_input = False
  lib = {}

  # initialization
  def __init__(self):
    self.SetConfiguration()
    self.ParseArguments()
    logging.basicConfig(format="[%(asctime)s][%(levelname)s] %(message)s", level=self.log_level, stream=self.error_file)
    signal.signal(signal.SIGINT, self.Shutdown)
    signal.signal(signal.SIGTERM, self.Shutdown)
    if self.pid_path is not None:
      with open(self.pid_path, "w") as pid_file:
        pid_file.write(str(os.getpid()))

  # create a new libcec_configuration
  def SetConfiguration(self):
    self.cecconfig.strDeviceName = "cecd"
    self.cecconfig.bActivateSource = 0
    self.cecconfig.bMonitorOnly = 1
    self.cecconfig.deviceTypes.Add(cec.CEC_DEVICE_TYPE_RECORDING_DEVICE)
    self.cecconfig.clientVersion = cec.LIBCEC_VERSION_CURRENT
    self.cecconfig.SetLogCallback(self.LogCallback)
    self.cecconfig.SetCommandCallback(self.CommandCallback)

  def ParseArguments(self):
    parser = argparse.ArgumentParser(description='CEC Daemon')
    parser.add_argument("-i", "--input", help="Input file path", type=str)
    parser.add_argument("-o", "--output", help="Output file path", type=str)
    parser.add_argument("-e", "--error", help="Error file path", type=str)
    parser.add_argument("-s", "--status", help="Status file path", type=str)
    parser.add_argument("-p", "--pid", help="PID file path", type=str)
    args = parser.parse_args()
    if args.input:
      self.input_path = args.input
    if args.output:
      self.output_file = open(args.output, "w", buffering=1)
    if args.error:
      self.error_file = open(args.error, "w", buffering=1)
    if args.status:
      self.status_path = args.status
    if args.pid:
      self.pid_path = args.pid

  # detect an adapter and return the com port path
  def DetectAdapter(self):
    retval = None
    adapters = self.lib.DetectAdapters()
    for adapter in adapters:
      logging.debug("Found a CEC adapter on port: %s", adapter.strComName)
      retval = adapter.strComName
    return retval

  # run daemon
  def Run(self):
    # init libCEC and print version and compilation information
    self.lib = cec.ICECAdapter.Create(self.cecconfig)
    logging.debug("libCEC version %s loaded: %s", self.lib.VersionToString(self.cecconfig.serverVersion), self.lib.GetLibInfo())

    # search for adapters
    adapter = self.DetectAdapter()
    if adapter == None:
      print("No adapters found", file=self.output_file)
    else:
      # open adapter
      if self.lib.Open(adapter):
        try:
          # refresh status
          self.ProcessCommandStatus()
          # start main loop
          self.MainLoop()
        except KeyboardInterrupt:
          logging.info("Caught KeyboardInterrupt, shutting down now")
        finally:
          self.lib.Close()
      else:
        print("Failed to open a connection to the CEC adapter", file=self.output_file)
    
    # close files
    self.output_file.close()
    self.error_file.close()

    # remove pid file
    if self.pid_path is not None:
      try:
        os.remove(self.pid_path)
      except FileNotFoundError:
        pass

  # main loop, read and process commands
  def MainLoop(self):
    self.ProcessCommandHelp()
    input_is_fifo = self.input_path is not None and stat.S_ISFIFO(os.stat(self.input_path).st_mode)
    while self.run_loop:
      self.read_input = True
      input_file = sys.stdin if self.input_path is None else open(self.input_path, "r")
      with input_file:
        for command in input_file:
          self.read_input = False
          self.ProcessCommand(command)
          if not self.run_loop:
            break
          self.read_input = True
      self.read_input = False
      if not input_is_fifo:
        self.run_loop = False

  # shutdown main loop
  def Shutdown(self, signum=None, frame=None):
    self.run_loop = False
    if self.read_input:
      self.read_input = False
      raise KeyboardInterrupt

  # transmit an arbitrary command
  def TransmitCommand(self, opcode):
    cmd = cec.cec_command()
    cec.cec_command.Format(cmd, cec.CECDEVICE_BROADCAST, self.device, opcode)
    if not self.lib.Transmit(cmd):
      print("Failed to send command", file=self.output_file)

  # process input command
  def ProcessCommand(self, command):
    command = command.strip().lower()
    if command == 'q' or command == 'quit':
      self.run_loop = False
    elif command == 'help':
      self.ProcessCommandHelp()
    elif command == 'on':
      self.ProcessCommandPowerOn()
    elif command == 'off':
      self.ProcessCommandPowerOff()
    elif command == 'status':
      self.ProcessCommandStatus()
    elif command[:2] == 'tx':
      self.ProcessCommandTx(command[3:])

  # show available commands
  def ProcessCommandHelp(self):
    print("Enter command: q[uit], on, off, status, tx <data>", file=self.output_file)

  # send a power on command
  def ProcessCommandPowerOn(self):
    self.WriteStatus(cec.CEC_POWER_STATUS_IN_TRANSITION_STANDBY_TO_ON)
    self.TransmitCommand(cec.CEC_OPCODE_IMAGE_VIEW_ON)

  # send a standby command
  def ProcessCommandPowerOff(self):
    self.WriteStatus(cec.CEC_POWER_STATUS_IN_TRANSITION_ON_TO_STANDBY)
    self.TransmitCommand(cec.CEC_OPCODE_STANDBY)

  # send a status command
  def ProcessCommandStatus(self):
    self.TransmitCommand(cec.CEC_OPCODE_GIVE_DEVICE_POWER_STATUS)

  # send a custom command
  def ProcessCommandTx(self, data):
    cmd = self.lib.CommandFromString(data)
    if self.lib.Transmit(cmd):
      print("Command sent", file=self.output_file)
    else:
      print("Failed to send command", file=self.output_file)

  # logging callback
  def LogCallback(self, level, time, message):
    if level == cec.CEC_LOG_ERROR:
      logging.error(message)
    elif level == cec.CEC_LOG_WARNING:
      logging.warning(message)
    elif level == cec.CEC_LOG_NOTICE:
      logging.info(message)
    elif level == cec.CEC_LOG_TRAFFIC:
      logging.debug(message)
    elif level == cec.CEC_LOG_DEBUG:
      logging.debug(message)
    return 0

  # command received callback
  def CommandCallback(self, cmd):
    logging.debug("Command received: " + cmd)
    parsed = self.lib.CommandFromString(cmd)
    if parsed.initiator == self.device:
      if parsed.opcode == cec.CEC_OPCODE_REQUEST_ACTIVE_SOURCE:
        self.WriteStatus(cec.CEC_POWER_STATUS_ON)
      elif parsed.opcode == cec.CEC_OPCODE_STANDBY:
        self.WriteStatus(cec.CEC_POWER_STATUS_STANDBY)
      elif parsed.opcode == cec.CEC_OPCODE_REPORT_POWER_STATUS:
        self.WriteStatus(parsed.parameters.At(0))
    return 0

  # write current status to file and display
  def WriteStatus(self, status):
    if status == cec.CEC_POWER_STATUS_ON or status == cec.CEC_POWER_STATUS_IN_TRANSITION_STANDBY_TO_ON:
      print("Status: on", file=self.output_file)
      if self.status_path is not None:
        with open(self.status_path, "w") as status_file:
          status_file.write("1\n")
    elif status == cec.CEC_POWER_STATUS_STANDBY or status == cec.CEC_POWER_STATUS_IN_TRANSITION_ON_TO_STANDBY:
      print("Status: off", file=self.output_file)
      if self.status_path is not None:
        with open(self.status_path, "w") as status_file:
          status_file.write("0\n")

# main function
if __name__ == '__main__':
  daemon = CecDaemon()
  daemon.Run()
