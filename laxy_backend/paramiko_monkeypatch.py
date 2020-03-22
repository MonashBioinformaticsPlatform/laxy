"""
Add binary-mode options to SSHClient.exec_command(...) for binary stdout, stderr channels.

From: https://gist.github.com/smurn/4d45a51b3a571fa0d35d
See: https://github.com/paramiko/paramiko/issues/291
"""
from typing import Tuple

import paramiko
from paramiko import ChannelFile, Channel


def _patched_exec_command(self,
                          command,
                          bufsize=-1,
                          timeout=None,
                          get_pty=False,
                          stdin_binary=True,
                          stdout_binary=True,
                          stderr_binary=True) -> Tuple[ChannelFile, ChannelFile, ChannelFile]:
    chan = self._transport.open_session()
    if get_pty:
        chan.get_pty()
    chan.settimeout(timeout)
    chan.exec_command(command)
    stdin = chan.makefile('wb' if stdin_binary else 'w', bufsize)
    stdout = chan.makefile('rb' if stdout_binary else 'r', bufsize)
    stderr = chan.makefile_stderr('rb' if stderr_binary else 'r', bufsize)
    return stdin, stdout, stderr


def _patched_exec_command_channel(self,
                                  command,
                                  bufsize=-1,
                                  timeout=None,
                                  get_pty=False,
                                  stdin_binary=True,
                                  stdout_binary=True,
                                  stderr_binary=True) -> Tuple[ChannelFile, ChannelFile, ChannelFile, Channel]:
    """
    This is equivalent to exec_command, but also returns the Channel so that we can grab
    the exit code (eg chan.recv_exit_status() ).
    """
    chan = self._transport.open_session()
    if get_pty:
        chan.get_pty()
    chan.settimeout(timeout)
    chan.exec_command(command)
    stdin = chan.makefile('wb' if stdin_binary else 'w', bufsize)
    stdout = chan.makefile('rb' if stdout_binary else 'r', bufsize)
    stderr = chan.makefile_stderr('rb' if stderr_binary else 'r', bufsize)
    return stdin, stdout, stderr, chan


paramiko.SSHClient.exec_command = _patched_exec_command
paramiko.SSHClient.exec_command_channel = _patched_exec_command_channel
