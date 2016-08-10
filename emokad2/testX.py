import numpy as np
import cmath
from scipy.signal import get_window
import time

#B = np.array([[1,2,3,4,5],[5,4,3,4,5],[1,2,2,3,2],[4,3,2,5,1]])
#C = np.array([[1,3,1,3,1],[1,3,2,4,2],[5,2,4,3,1]])

# Spectral inversion
def fspecinv(b,filtorder):
    b = -b
    b[int(filtorder/2)] = b[int(filtorder/2)] + 1
    return b

# Compute filter kernel
def fkernel(filtorder, f, win):
    
    b = np.arange(filtorder)
    #h = np.arange(filtorder)
    #j = np.arange(filtorder)
    for i in (xrange(int(filtorder))):
        #print i-(np.floor(filtorder/2))
        #h[i] = (i-(np.floor(filtorder/2)))
        if i-(np.floor(filtorder/2)) == 0 :
            b[i] = 2 * np.pi * f 						# No division by zero
        else :
            b[i] = np.sin(2 * np.pi * f * (i-(np.floor(filtorder/2)))) / np.array(i-(np.floor(filtorder/2))) 			# Sinc        

    b2 = b * win												# Window Sinc
    b3 = b2 / sum(b2)	 
    return b3      

def firws(filtorder, freq, win):

    freq = freq / 2

    b = fkernel(filtorder, freq[0], win)

    c = b + fspecinv(fkernel(filtorder, freq[1], win),filtorder)
    
    winsinc = fspecinv(c,filtorder)

    return winsinc

def Bandpass(data2,lowcutoff,highcutoff,fs):

	transwidthratio = 0.25

	fnyq = fs/2


	maxTWBArray = [lowcutoff, fnyq-highcutoff]

	maxDf = min(maxTWBArray)

	df = min([max([maxTWBArray[0] * transwidthratio, 2.0]),maxDf])

	filtorder = 3.3 / (df / fs) # Hamming window
	filtorder = np.ceil(filtorder / 2) * 2  + 1 # Filter order must be even. +1 for centerpoint window

	#print np.array([range(int(filtorder))])

	win = get_window('hamming',filtorder)

	cutoffarray = np.array([lowcutoff,highcutoff]) + [-df/2,df/2] # bandpass

	winsinc = firws(filtorder, cutoffarray / fnyq, win)

	#np.savetxt("conv.txt", winsinc, fmt='%10.8f', delimiter='\n')

	banpassed = np.transpose(np.arange(data2.shape[0]))
	for j in range(data2.shape[1]):
		banpassed = np.vstack([banpassed,np.convolve((data2[:,j]),(winsinc), mode='same')])
		#print banpassed.shape
	return banpassed[1:data2.shape[1]+1,:]


# FUNGSI PEMBUAT SINYAL REFERENCE
def refSignal(t, fs, f): 
# t  = panjang waktu sinyal reference (sekond)
# fs = frekuensi sampling
# f  = frekuensi stimulus / reference
	Ref = []
	p = 1000;
	TP = xrange(1,t*fs+1) # dimulai dari array 1 (bukan 0), berakhir di nilai sinecos= 0 atau 1.
	for j in TP:
		# (np.allclose(np.sin(2*np.pi*f*j/fs), 0), bernilai True(1), jika nilainya mendekati 0.
		# !np.allclose digunakan untuk memberikan nilai 0 ketika nilai 2*pi hasilnya tidak tepat 0.
		# Sinh1 = ~(np.allclose(np.sin(2*np.pi*f*j/fs), 0))*20*np.sin(2*np.pi*f*j/fs); 
		Sinh1 = np.sin(2*np.pi*f*j/fs); 
		Cosh1 = np.cos(2*np.pi*f*j/fs);
		Sinh2 = np.sin(2*np.pi*2*f*j/fs);
		Cosh2 = np.cos(2*np.pi*2*f*j/fs);
		Ref.append([Sinh1,Cosh1,Sinh2,Cosh2])
	return np.array(Ref) #np.asmatrix(Ref)
#

# FUNGSI PENGHITUNG NILAI CCA SEDERHANA
# SYARAT : JUMLAH CHANNEL < JUMLAH EPOCH (time point).
# jika channel lebih banyak, maka matrix harus di transpose
# X = data, Y = reference, t1 = epoch awal data, t2 = epoch akhir data
def cca(X,Y,t1,t2):
	#time.sleep(1)
	# cek channel < epoch, untuk data eeg, harus di transpose karena datanya terbalik dgn matlab 
	[rowX,colX] = X.shape  
	[rowY,colY] = Y.shape
	if rowX > colX :
		X = np.transpose(X)
		[rowX,colX] = X.shape  
	if rowY > colY :
		Y = np.transpose(Y)
		[rowY,colY] = Y.shape  

	#XY = np.asmatrix(np.hstack([data2[0:512,:],Ref]))  # [X;Y]
	XY = np.asmatrix(np.vstack([X[:,t1:t2],Y]))  # [X;Y]



	COV = np.cov(XY) # Covariance [X;Y]
	[rowCOV,colCOV] = COV.shape

	# http://qaoverflow.com/question/numpy-possible-for-zero-determinant-matrix-to-be-inverted/
	# Pada matlab, inverse matrix yang tidak positive definit tidak bisa dilakukan
	# Biasanya matrix harus di tambah, suatu matrix identitas dengan nilai yang kecil mendekati 0.
	# atau dimensinya harus diubah dengan menggunakan SVD->dekomposisi->rekonstruksi ulang matrix.
	# namun, hasilnya adalah positive semi-definit, artinya masih mungkin memiliki determinant 0.
	# Positive semi-definit, dapat diatasi dengan metode Moore-Penrose pseudoinverse (pinv)

	InvCxx = np.asmatrix(np.linalg.pinv(COV[0:rowX,0:rowX] + np.finfo(float).eps)) # Tikhonov correction (X+nI with n->0)
	InvCyy = np.asmatrix(np.linalg.pinv(COV[rowX:rowCOV,rowX:colCOV] + np.finfo(float).eps))
	Cxy = np.asmatrix(COV[0:rowX,rowX:colCOV])
	Cyx = np.asmatrix(np.transpose(Cxy))

	[r2,Wx] = np.linalg.eig(InvCxx*Cxy*InvCyy*Cyx)

	# np.sqrt tidak bisa mengakarkan nilai negatif. Kecuali jika bentuk datanya adalah complex
	# Karena itu, di tambah imaginer yang bernilai mendekati 0.
	r = np.real(np.sqrt(r2 + (np.finfo(float).eps * 1j))) 
	return r



#print max(r)
#print time.time()*1000.0 - ms

# def Itung(data2,f):
# 	t = 1		# panjang waktu sinyal reference (sekond)
# 	fs = 256	# frekuensi sampling
# 	##f = 10		# frekuensi stimulus / reference
# 	t1 = 100*256		# sampling data dari epoch ke 0
# 	t2 = 101*256	# sampling data berakhir di epoch ke 512

# 	lowcutoff = 8
# 	highcutoff = 30
# 	data = Bandpass.Bandpass(data2,lowcutoff,highcutoff,fs)

# 	Ref = refSignal(t,fs,f) # Reference Signal
# 	r = cca(data,Ref,t1,t2)

# 	return max(r)
