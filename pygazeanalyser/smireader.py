#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of PyGaze - the open-source toolbox for eye tracking
#
# PyGazeAnalyser is a Python module for easily analysing eye-tracking data
# Copyright (C) 2014  Edwin S. Dalmaijer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

# SMI Reader
#
# Reads files as produced by SMI Tools IDF converter.  The converter produces
# two separate files: Events and Samples.  The events file contains the
# Fixations, Saccades, and Blinks as determined by SMI's tools.  The samples
# file contains raw eyetracker gaze information.
#
# Starting and stopping the capture capability results in the Trial Number
# recorded for each event being incremented.  Currently, this is the
# mechanism by which the read_smioutput method is limited.  As a result,
# when conducting the experiment, the eyetracker needs to be started and
# stopped as necessary to properly delineate between images.
#
# (C) Terry Meacham, 2015
# terry.t.meacham@gmail.com
#
# Based on eyetribereader.py written by Edwin S. Dalmaijer (C) 2014
#
# version 1 (26-01-2015)

# __author__ = "Terry Meacham"


import copy
import os.path
import re
import numpy

class SMIModes:
  LEFT_ONLY = 0
  RIGHT_ONLY = 1
  AVERAGE = 2
  STRICT_AVERAGE = 3
  STANDARD_EVENTS = ('Fixation L', 'Saccade L', 'Blink L', 'Fixation R', 'Saccade R', 'Blink R')

def read_smioutput(filename, start=None, ag_mode=None, stop=None, debug=False):

  """Returns a list with dicts for every trial. A trial dict contains the
  following keys:
    events        - dict with the following keys:
            Efix  - list of lists, each containing [starttime, endtime, duration, endx, endy]
            Esac  - list of lists, each containing [starttime, endtime, duration, startx, starty, endx, endy]
            Eblk  - list of lists, each containing [starttime, endtime, duration]
            msg   - list of lists, each containing [time, message]
            NOTE: timing is in system time of the SMI iView machine!

  arguments

  filename  - path to the file that has to be read
  start     - trial start number

  keyword arguments

  ag_mode    - SMI produces Left and Right eye event output.  The mode specifies
              how to handle the presence or absense of each eye.
    = SMIModes.LEFT_ONLY      (0) - Use only the left eye.
    = SMIModes.RIGHT_ONLY     (1) - Use only the right eye.
    = SMIModes.AVERAGE        (2) - Use only the left eye.
    = SMIModes.AVERAGE_STRICT (3) - Use only the left eye.
  stop      - trial to stop on (default = None)
  debug     - Boolean indicating if DEBUG mode should be on or off;
              if DEBUG mode is on, information on what the script
              currently is doing will be printed to the console
              (default = False)

  returns

  data    - a list with a dict for every trial (see above)
  """

  # variables
  data = []
  fixs = [{}, {}]
  sacs = [{}, {}]
  blks = [{}, {}]
  events = {'Efix':[],'Esac':[],'Eblk':[],'msg':[]}
  starttime = None
  started = False
  trialend = False
  trial_id = None
  content = False

  # # # # #
  # debug mode

  if debug:
    def message(msg):
      print(msg)
  else:
    def message(msg):
      pass

  def normalize(lines):
    length = len(lines[0])
    if len(lines[0]) == len(lines[1]):
      if len(lines[0]) == 0 and len(lines[1]) == 0:
        message('Lists are empty.')
        return

    equal = (lines[0].keys() == lines[1].keys())

    if not equal:

      for key in lines[1].keys():
        if lines[0].get(key, None) is None:
          lines[0][key] = None
          message('Adding missing key left: %s' % key)
          message(lines[1][key])

      for key in lines[0].keys():
        if lines[1].get(key, None) is None:
          lines[1][key] = None
          message('Adding missing key right: %s' % key)
          message(lines[0][key])

      if lines[0].keys() == lines[1].keys():
        message('Lists are now equal.')

  def process_fixation(mode, lr):
    """
    Table Header for Fixations:
    EventType, Trial, Number, Start, End, Duration, LocX, LocY,
      DispersionX, DispersionY, Plane, AvgPupilSizeX, AvgPupilSizeY

    Efix: [starttime, endtime, duration, endx, endy]

    Fixation L  1 14  3382450806427 3382450965523 159096  996.68  569.56  22  69  -1  17.16 17.16
    """

    normalize(lr)
    left = lr[0]
    right = lr[1]

    keys = sorted(left.keys())

    result = []
    for key in keys:
      l = left[key]
      r = right[key]

      if mode == SMIModes.AVERAGE or mode is None:
        if l is None:
          result.append(r[3:8])
        elif r is None:
          result.append(l[3:8])
        else:
          result.append([l[3], l[4], (l[5] + r[5])/2, (l[6] + r[6])/2,
                        (l[7] + r[7])/2])

      elif mode == SMIModes.LEFT_ONLY:
        if l is None:
          continue

        result.append(l[3:8])

      elif mode == SMIModes.RIGHT_ONLY:
        if r is None:
          continue

        result.append(r[3:8])

      elif mode == SMIModes.STRICT_AVERAGE:
        if l is None or r is None:
          continue

        result.append([l[3], l[4], (l[5] + r[5])/2, (l[6] + r[6])/2,
                       (l[7] + r[7])/2])

    return result


  def process_saccade(mode, lr):
    """
    Table Header for Saccades:
    EventType, Trial, Number, Start, End, Duration, StartLocX, StartLocY,
      EndLocX, EndLocY, Amplitude, PeakSpeed, PeakSpeedAt, AverageSpeed,
      PeakAccel, PeakDecel, AverageAccel

    Esac: [starttime, endtime, duration, startx, starty, endx, endy]

    Saccade L 1 13  3382450786556 3382450806427 19871 1009.68 587.24  1000.98 583.28  0.11  9.00  1.00  5.74  94.46 -203.67 137.37
    """

    normalize(lr)
    left = lr[0]
    right = lr[1]

    keys = sorted(left.keys())

    result = []
    for key in keys:
      l = left[key]
      r = right[key]

      if mode == SMIModes.AVERAGE or mode is None:
        if l is None:
          result.append(r[3:10])
        elif r is None:
          result.append(l[3:10])
        else:
          result.append([l[3], l[4], l[5], (l[6] + r[6])/2, (l[7] + r[7])/2,
                        (l[8] + r[8])/2, (l[9] + r[9])/2])

      elif mode == SMIModes.LEFT_ONLY:
        if l is None:
          continue

        result.append(l[3:10])

      elif mode == SMIModes.RIGHT_ONLY:
        if r is None:
          continue

        result.append(r[3:10])

      elif mode == SMIModes.STRICT_AVERAGE:
        if l is None or r is None:
          continue

        result.append([l[3], l[4], l[5], (l[6] + r[6])/2, (l[7] + r[7])/2,
                      (l[8] + r[8])/2, (l[9] + r[9])/2])
    return result


  def process_blink(mode, lr):
    """
    Table Header for Blinks:
    EventType, Trial, Number, Start, End, Duration

    Eblk: [starttime, endtime, duration]

    Blink L 1 1 3382451084874 3382451164475 79601
    """

    normalize(lr)
    left = lr[0]
    right = lr[1]

    keys = sorted(left.keys())

    result = []
    for key in keys:
      l = left[key]
      r = right[key]

      if l is None:
        result.append(r[3:6])
      elif r is None:
        result.append(l[3:6])
      else:
        continue

    return result

  def append_line(ln, lst):
    if re.match(r'.*L$', ln[0]):
      lst[0][ln[2]] = ln
    elif re.match(r'.*R$', line[0]):
      lst[1][ln[2]] = ln
    else:
      message('Uknown fixation ident. "%s"' % re.match(r' L', ln[0]))

  # # # # #
  # file handling

  # check if the file exists
  if os.path.isfile(filename):
    # open file
    message("opening file '%s'" % filename)
    f = open(filename, 'r')
  # raise exception if the file does not exist
  else:
    raise Exception("Error in read_smioutput: file '%s' does not exist" % filename)

  # read file contents
  message("reading file '%s'" % filename)
  raw = f.readlines()

  # close file
  message("closing file '%s'" % filename)
  f.close()

  # loop through all lines
  for i in range(len(raw)):

    # string to list
    line = raw[i].replace('\n','').replace('\r','').split('\t')

    if content == False and line[0] not in SMIModes.STANDARD_EVENTS:
      continue

    content = True

    old_trial = trial_id
    trial_id = int(line[1])

    if old_trial is not None and old_trial != trial_id:
      trialend = True

    # check if trial has already started
    if started:

      # only check for stop if there is one
      if stop == trial_id or i == len(raw)-1:
        started = False
        trialend = True

      # trial ending
      if trialend:
        message("trialend %s" % len(data))
        message('oldtrial: %d\nnewtrial: %d' % (old_trial, trial_id))
        message('processing contents')

        events['Efix'] = process_fixation(ag_mode, fixs)
        events['Esac'] = process_saccade(ag_mode, sacs)
        events['Eblk'] = process_blink(ag_mode, blks)

        # trial dict
        trial = {}
        trial['events'] = copy.deepcopy(events)

        # add trial to data
        data.append(trial)

        # reset stuff
        events = {'Efix':[],'Esac':[],'Eblk':[],'msg':[]}

        fixs = [{}, {}]
        sacs = [{}, {}]
        blks = [{}, {}]
        trialend = False

        message('processing end')
        if started:
          message("trialstart %d" % len(data))

    # check if the current line contains start message
    else:
      if start is None or start == trial_id:
        message("trialstart %d" % len(data))
        started = True
        starttime = int(line[3])

    line[3] = int(line[3]) - starttime
    line[4] = int(line[4]) - starttime 
    line[5] = int(line[5])

    line[3:6] = [x/1000.0 for x in line[3:6]]

    # # # # #
    # parse line

    if started:
      """
        Message lines will start with a user specified event, followed by
        trial number, time, and description.

        Table Header for User Events:
        Event Type  Trial Number  Start Description
      """

      if line[0] not in SMIModes.STANDARD_EVENTS:
        time = int(line[2])
        msg = line[3]
        events['msg'].append([time, msg])

      else:
        try:
          event_type = line[0]
          m = None
          if re.match(r'^Fixation.*', event_type) is not None:
            line[6] = float(line[6])
            line[7] = float(line[7])
            append_line(line, fixs)
          elif re.match(r'^Saccade.*', event_type) is not None:
            line[6] = float(line[6])
            line[7] = float(line[7])
            line[8] = float(line[8])
            line[9] = float(line[9])
            append_line(line, sacs)
          elif re.match(r'^Blink.*', event_type) is not None:
            append_line(line, blks)
        except Exception as e:
          message("line '%s' could not be parsed: %s" % (line, e))
          continue # skip this line

  # # # # #
  # return

  return data

# DEBUG #
if __name__ == "__main__":
  data = read_smioutput('events.txt', 1, stop=5, ag_mode=SMIModes.RIGHT_ONLY, debug=False)
  print data[0]['events']['Efix']
# # # # #