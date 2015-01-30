#!/usr/bin/env python
# analysis script for natural viewing experiment
#
# version 1 (1 Mar 2014)

__author__ = "Edwin Dalmaijer"

# native
import os

# custom
from pygazeanalyser.smireader import read_smioutput, SMIModes
from pygazeanalyser.gazeplotter import draw_fixations, draw_heatmap, draw_scanpath, draw_raw

# external
import numpy


# # # # #
# CONSTANTS

# PARTICIPANTS
PPS = ['1']

# DIRECTORIES
# paths
DIR = os.path.dirname(__file__)
DATADIR = IMGDIR = os.path.join(DIR, 'imgs')
PLOTDIR = os.path.join(DIR, 'plots')

OUTPUTFILENAME = os.path.join(DIR, "output.txt")
# check if the image directory exists
if not os.path.isdir(IMGDIR):
	raise Exception("ERROR: no image directory found; path '%s' does not exist!" % IMGDIR)
# check if the data directory exists
if not os.path.isdir(DATADIR):
	raise Exception("ERROR: no data directory found; path '%s' does not exist!" % DATADIR)
# check if output directorie exist; if not, create it
if not os.path.isdir(PLOTDIR):
	os.mkdir(PLOTDIR)

# DATA FILES
SEP = '\t' # value separator
START_TRIAL = None # file trial number start message
STOP_TRIAL = None # file trial number end message

# EXPERIMENT SPECS
DISPSIZE = (1920,1080) # (px,px)
SCREENSIZE = (39.9,29.9) # (cm,cm)
SCREENDIST = 61.0 # cm
PXPERCM = numpy.mean([DISPSIZE[0]/SCREENSIZE[0],DISPSIZE[1]/SCREENSIZE[1]]) # px/cm

# # # # #
# READ FILES
# ---------
# loop through all participants
for ppname in PPS:
	
	print("starting data analysis for participant '%s'" % (ppname))
	
	# path
	fp = os.path.join(DATADIR, '%s.txt' % ppname)
	
	# open the file
	fl = open(fp, 'r')
	
	# read the file content
	data = fl.readlines()
	
	# close the file
	fl.close()
	
	# separate header from rest of file
	header = data.pop(0)
	header = header.replace('\n','').replace('\r','').replace('"','').split(SEP)
	
	# process file contents
	for i in range(len(data)):
		data[i] = data[i].replace('\n','').replace('\r','').replace('"','').split(SEP)
	
	# GAZE DATA
	print("loading gaze data")
	
	# path
	fp = os.path.join(DATADIR, 'events.txt')

	# read the file
	smidata = read_smioutput(fp, START_TRIAL, ag_mode=SMIModes.LEFT_ONLY, stop=STOP_TRIAL, debug=False)
	
	# NEW OUTPUT DIRECTORIES
	# create a new output directory for the current participant
	pplotdir = os.path.join(PLOTDIR, ppname)
	# check if the directory already exists
	if not os.path.isdir(pplotdir):
		# create it if it doesn't yet exist
		os.mkdir(pplotdir)

	# # # # #
	# PLOTS
	
	print("plotting gaze data")

	# loop through trials
	for trialnr in range(len(data)):
		
		# load image name, saccades, and fixations
		imgname = data[trialnr][header.index("image")]
		saccades = smidata[trialnr]['events']['Esac'] # [starttime, endtime, duration, startx, starty, endx, endy]
		fixations = smidata[trialnr]['events']['Efix'] # [starttime, endtime, duration, endx, endy]
		
		# paths
		imagefile = os.path.join(IMGDIR, imgname)

		rawplotfile = os.path.join(pplotdir, "raw_data_%s_%d" % (ppname,trialnr))
		scatterfile = os.path.join(pplotdir, "fixations_%s_%d" % (ppname,trialnr))
		scanpathfile =  os.path.join(pplotdir, "scanpath_%s_%d" % (ppname,trialnr))
		heatmapfile = os.path.join(pplotdir, "heatmap_%s_%d" % (ppname,trialnr))
		
		# raw data points
		# draw_raw(smidata[trialnr]['x'], smidata[trialnr]['y'], DISPSIZE, imagefile=imagefile, savefilename=rawplotfile)

		# fixations
		draw_fixations(fixations, DISPSIZE, imagefile=imagefile, durationsize=True, durationcolour=False, alpha=0.5, savefilename=scatterfile)
		
		# scanpath
		draw_scanpath(fixations, saccades, DISPSIZE, imagefile=imagefile, alpha=0.5, savefilename=scanpathfile)

		# heatmap		
		draw_heatmap(fixations, DISPSIZE, imagefile=imagefile, durationweight=True, alpha=0.5, savefilename=heatmapfile)
