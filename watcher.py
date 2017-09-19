#!/usr/bin/env python

import sys, os
import ctypes
import wave
import sys
import time
import glob
import yaml
import os

pa = ctypes.cdll.LoadLibrary('libpulse-simple.so.0')

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

def play(filename):
    """Play a WAV file with PulseAudio."""

    # Opening a file.
    wf = wave.open(filename, 'rb')

    # Defining sample format.
    ss = struct_pa_sample_spec()
    ss.rate = wf.getframerate()
    ss.channels = wf.getnchannels()
    ss.format = PA_SAMPLE_S16LE
    error = ctypes.c_int(0)

    # Creating a new playback stream.
    s = pa.pa_simple_new(
        None,  # Default server.
        filename,  # Application's name.
        PA_STREAM_PLAYBACK,  # Stream for playback.
        None,  # Default device.
        'playback',  # Stream's description.
        ctypes.byref(ss),  # Sample format.
        None,  # Default channel map.
        None,  # Default buffering attributes.
        ctypes.byref(error)  # Ignore error code.
    )
    if not s:
        raise Exception('Could not create pulse audio stream: {0}!'.format(
            pa.strerror(ctypes.byref(error))))

    while True:
        # Getting latency.
        latency = pa.pa_simple_get_latency(s, error)
        if latency == -1:
            raise Exception('Getting latency failed!')

        #print('{0} usec'.format(latency))

        # Reading frames and writing to the stream.
        buf = wf.readframes(BUFFSIZE)
        if buf == '':
            break

        if pa.pa_simple_write(s, buf, len(buf), error):
            return
            #raise Exception('Could not play file!')

    wf.close()

    # Waiting for all sent data to finish playing.
    if pa.pa_simple_drain(s, error):
        raise Exception('Could not simple drain!')

    # Freeing resources and closing connection.
    pa.pa_simple_free(s)


def main(argv):
    system_map = None
    chat_name = None

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
                            play(os.path.join(base_dir, "wav", "%s.wav" % level))
                print (latest_data)
            else:
                time.sleep(1)
            p = f.tell()
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv)

