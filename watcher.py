#!/usr/bin/env python

import sys, os
import ctypes
import wave
import sys
import time
import glob
import yaml
import os

PA_STREAM_PLAYBACK = 1
PA_SAMPLE_S16LE = 3
BUFFSIZE = 1024

class struct_pa_sample_spec(ctypes.Structure):
    __slots__ = [
        'format',
        'rate',
        'channels',
    ]

struct_pa_sample_spec._fields_ = [
    ('format', ctypes.c_int),
    ('rate', ctypes.c_uint32),
    ('channels', ctypes.c_uint8),
]
pa_sample_spec = struct_pa_sample_spec  # /usr/include/pulse/sample.h:174

class pa_playback(object):
    def __init__(self):
        self.pa = ctypes.cdll.LoadLibrary('libpulse-simple.so.0')
        self.s = None
        # Defining sample format.
        self.ss = struct_pa_sample_spec()
        self.ss.format = PA_SAMPLE_S16LE
        with wave.open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "wav", "red.wav"), 'rb') as wf:
            self.ss.rate = wf.getframerate()
            self.ss.channels = wf.getnchannels()
        self.error = ctypes.c_int(0)
        self.pa_app_name = ctypes.c_char_p("intel_watcher".encode('utf-8'))
        self.pa_stream_name = ctypes.c_char_p("alerts".encode('utf-8'))

    def create(self):
        # Creating a new playback stream.
        self.s = self.pa.pa_simple_new(
            None,  # Default server.
            self.pa_app_name,  # Application's name.
            PA_STREAM_PLAYBACK,  # Stream for playback.
            None,  # Default device.
            self.pa_stream_name,  # Stream's description.
            ctypes.byref(self.ss),  # Sample format.
            None,  # Default channel map.
            None,  # Default buffering attributes.
            ctypes.byref(self.error)  # Ignore error code.
        )
        if not self.s:
            raise Exception('Could not create pulse audio stream: {0}!'.format(
                self.pa.strerror(ctypes.byref(self.error))))

    def play(self, filename):
        """Play a WAV file with PulseAudio."""

        # Opening a file.
        with wave.open(filename, 'rb') as wf:
            while True:
                # Getting latency.
                latency = self.pa.pa_simple_get_latency(self.s, self.error)
                if latency == -1:
                    raise Exception('Getting latency failed!')

                # Reading frames and writing to the stream.
                buf = wf.readframes(BUFFSIZE)
                if buf == '':
                    break

                if self.pa.pa_simple_write(self.s, buf, len(buf), self.error):
                    return

        # Waiting for all sent data to finish playing.
        if self.pa.pa_simple_drain(s, error):
            raise Exception('Could not simple drain!')

        # Freeing resources and closing connection.
        self.pa.pa_simple_free(self.s)


def main(argv):
    system_map = None
    chat_name = None
    playback_system = pa_playback()
    playback_system.create()

    try:
        logs_path = sys.argv[1:][0]
    except:
        logs_path = None

    base_dir = os.path.dirname(os.path.realpath(__file__))

    print ("[ii] Loading configuration.")

    try:
        with open(os.path.join(base_dir, 'settings.yaml'), 'r') as f:
            config_file = yaml.load(f)
            system_map = config_file['watcher']['system_map']
            chat_name = config_file['watcher']['chat_name']
            if not logs_path:
                try:
                    logs_path = config_file['watcher']['logs_path']
                except KeyError:
                    pass
        if not logs_path:
            # try to guess
            logs_path = os.path.join(os.getenv("HOME"), 'Documents', 'EVE', 'logs', 'Chatlogs')
            if not os.path.exists(logs_path):
                logs_path = os.path.join(os.getenv("HOME"), '.wine', 'drive_c', 'users', os.getenv("LOGNAME"), 'My Documents', 'EVE', 'logs', 'Chatlogs')

        if not chat_name:
            raise RuntimeError("Can't get the chat name. Looks like 'chat_name' option is empty?")
    except KeyError as exp:
        print ("[EE] Can't fine key: '%s'" % exp)
        print ("[EE] Malformed settings.yaml file. See settings_example.yaml for a reference.")
        sys.exit(3)
    except FileNotFoundError as exp:
        print ("[EE] %s" % exp)
        print ("[EE] Can't open settings.yaml file. Have you created a copy of settings_example.yaml?")
        sys.exit(3)
    except RuntimeError as exp:
        print ("[EE] %s" % exp)
        sys.exit(3)

    print ("[ii] Watchman started.")

    logs_glob = os.path.join(logs_path, "%s_*.txt" % chat_name)

    list_of_files = glob.glob(logs_glob) # * means all if need specific format then *.csv

    if not list_of_files:
        print ("[EE] No files found for glob: '%s'. Incorrect chat name?" % logs_glob)
        sys.exit(3)

    l_file = max(list_of_files, key=os.path.getctime)

    print ("[ii] Using log file as a Intel source: %s" % l_file)

    for level in ['red', 'yellow', 'green']:
        print ("[ii] + %s alers for system:" % level)
        for system in system_map[level]:
            print (" - %s" % system)
    print ("[ii] Ok. Running the monitor...")
    p = 0
    with open(l_file, 'rb') as f:
        while True:
            f.seek(p)
            latest_data = f.read()
            if latest_data and p:
                latest_data = latest_data.decode("utf-16").strip("\n")
                for level in ['red', 'yellow', 'green']:
                    for system in system_map[level]:
                        if system in latest_data:
                            print ("-ALERT- %s" % level)
                            playback_system.play(os.path.join(base_dir, "wav", "%s.wav" % level))
                print (latest_data)
            else:
                time.sleep(1)
            p = f.tell()
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv)

