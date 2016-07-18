import numpy as np
import cmath
import matplotlib.pyplot as plt


def firws(filtorder, freq, win):

    freq = freq / 2

    b = fkernel(filtorder, freq[0], win)

    c = b + fspecinv(fkernel(filtorder, freq[1], win),filtorder)
    
    winsinc = fspecinv(c,filtorder)

    return winsinc

# Compute filter kernel
def fkernel(filtorder, f, win):
    
    b = np.arange(filtorder)
    #h = np.arange(filtorder)
    #j = np.arange(filtorder)
    for i in (range(int(filtorder))):
        #print i-(np.floor(filtorder/2))
        #h[i] = (i-(np.floor(filtorder/2)))
        if i-(np.floor(filtorder/2)) == 0 :
            b[i] = 2 * np.pi * f 						# No division by zero
        else :
            b[i] = np.sin(2 * np.pi * f * (i-(np.floor(filtorder/2)))) / np.array(i-(np.floor(filtorder/2))) 			# Sinc        

    b2 = b * win												# Window Sinc
    b3 = b2 / sum(b2)	 
    return b3                                                    # Spectral inversion

def fspecinv(b,filtorder):
    b = -b
    b[(np.floor(filtorder/2))] = b[(np.floor(filtorder/2))] + 1
    return b
