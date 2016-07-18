import numpy as np
import cmath
from scipy.signal import *
import firws

#import math
import matplotlib.pyplot as plt

def Bandpass(data2,lowcutoff,highcutoff,fs):

	transwidthratio = 0.25

	fnyq = fs/2


	maxTWBArray = [lowcutoff, fnyq-highcutoff]

	maxDf = min(maxTWBArray)

	df = min([max([maxTWBArray[0] * transwidthratio, 2]),maxDf])


	filtorder = 3.3 / (df / fs) # Hamming window
	filtorder = np.ceil(filtorder / 2) * 2  + 1 # Filter order must be even. +1 for centerpoint window

	#print np.array([range(int(filtorder))])

	win = get_window('hamming',filtorder)

	cutoffarray = np.array([lowcutoff,highcutoff]) + [-df/2,df/2] # bandpass

	winsinc = firws.firws(filtorder, cutoffarray / fnyq, win)

	banpassed = np.transpose(np.arange(data2.shape[0]))
	for j in range(data2.shape[1]):
		banpassed = np.vstack([banpassed,np.convolve((data2[:,j]),(winsinc), mode='same')])
		#print banpassed.shape
	return banpassed[1:data2.shape[1]+1,:]