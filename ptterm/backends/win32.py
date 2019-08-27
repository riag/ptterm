from __future__ import unicode_literals

from prompt_toolkit.eventloop import get_event_loop
from prompt_toolkit.eventloop.future import Future

import winpty
import winpty.cywinpty
from winpty.cywinpty import Agent
import psutil

import abc
import os
import six
import time

from .base import Terminal
from .win32_pipes import PipeReader, PipeWriter

__all__ = [
    'Win32Terminal',
]

class Pty(Agent):
    def __init__(self, cols, rows):
        Agent.__init__(self, cols, rows, True)

    def conin_name(self):
        return self.conin_pipe_name

    def conout_name(self):
        return self.conout_pipe_name

    def close(self):
        pass

class Win32Terminal(Terminal):
    """
    Terminal backend for Windows, on top of winpty.
    """
    def __init__(self, command):
        self.pty = Pty(120, 24)
        self.ready_f = Future()
        self._input_ready_callbacks = []
        self.loop = get_event_loop()
        self.command = command

        # Open input/output pipes.
        def received_data(data):
            self._buffer.append(data)
            for cb in self._input_ready_callbacks:
                cb()

        self.stdout_pipe_reader = PipeReader(
            self.pty.conout_name(),
            read_callback=received_data,
            done_callback=lambda: self.ready_f.set_result(None))

        self.stdin_pipe_writer = PipeWriter(
            self.pty.conin_name())

        # Buffer in which we read + reading flag.
        self._buffer = []

    def add_input_ready_callback(self, callback):
        """
        Add a new callback to be called for when there's input ready to read.
        """
        self._input_ready_callbacks.append(callback)
        if self._buffer:
            callback()

    def read_text(self, amount):
        " Read terminal output and return it. "
        result = ''.join(self._buffer)
        self._buffer = []
        return result

    def write_text(self, text):
        " Write text to the stdin of the process. "
        self.stdin_pipe_writer.write(text)

    def connect_reader(self):
        """
        Connect the reader to the event loop.
        """
        self.stdout_pipe_reader.start_reading()

    def disconnect_reader(self):
        """
        Connect the reader to the event loop.
        """
        self.stdout_pipe_reader.stop_reading()

    @property
    def closed(self):
        return self.ready_f.done()

    def set_size(self, width, height):
        " Set terminal size. "
        self.pty.set_size(width, height)

    def start(self):
        """
        Start the terminal process.
        """
        # self.pty.spawn(SpawnConfig(
        #     SpawnConfig.flag.auto_shutdown,
        #     cmdline=r'C:\windows\system32\cmd.exe'))
        #self.pty.spawn(None, cmdline=self.command)
        cmd = self.command
        if isinstance(cmd, (list, tuple)):
            cmd = ' '.join(cmd)
        self.pty.spawn('', cmdline=cmd)

    def kill(self):
        " Terminate the process. "
        self.pty.close()

    def get_name(self):
        """
        Return the name for this process, or `None` when unknown.
        """ 
        p = psutil.Process(self.pty.pid)
        return p.name()

    def get_cwd(self):
        p = psutil.Process(self.pty.pid)
        return p.cwd()
