import numpy as np
import cmath
#import math
import matplotlib.pyplot as plt
import Bandpass

data2= np.genfromtxt('book.csv', delimiter=',')

B = np.array([[1,2,3,4,5],[5,4,3,4,5],[1,2,2,3,2],[4,3,2,5,1]])
C = np.array([[1,3,1,3,1],[1,3,2,4,2],[5,2,4,3,1]])



#b    = np.matrix(np.array(data))
#data = np.asmatrix(data2)

# FUNGSI PEMBUAT SINYAL REFERENCE
def refSignal(t, fs, f): 
# t  = panjang waktu sinyal reference (sekond)
# fs = frekuensi sampling
# f  = frekuensi stimulus / reference
	Ref = []
	p = 1000;
	TP = range(1,t*fs+1) # dimulai dari array 1 (bukan 0), berakhir di nilai sinecos= 0 atau 1.
	for j in TP:
		# (np.allclose(np.sin(2*np.pi*f*j/fs), 0), bernilai True(1), jika nilainya mendekati 0.
		# !np.allclose digunakan untuk memberikan nilai 0 ketika nilai 2*pi hasilnya tidak tepat 0.
		Sinh1 = ~(np.allclose(np.sin(2*np.pi*f*j/fs), 0))*np.sin(2*np.pi*f*j/fs); 
		Cosh1 = ~(np.allclose(np.cos(2*np.pi*f*j/fs), 0))*np.cos(2*np.pi*f*j/fs);
		Sinh2 = ~(np.allclose(np.sin(2*np.pi*2*f*j/fs), 0))*np.sin(2*np.pi*2*f*j/fs);
		Cosh2 = ~(np.allclose(np.cos(2*np.pi*2*f*j/fs), 0))*np.cos(2*np.pi*2*f*j/fs);
		Ref.append([Sinh1,Cosh1,Sinh2,Cosh2])
	return np.array(Ref) #np.asmatrix(Ref)
#

# FUNGSI PENGHITUNG NILAI CCA SEDERHANA
# SYARAT : JUMLAH CHANNEL < JUMLAH EPOCH (time point).
# jika channel lebih banyak, maka matrix harus di transpose
# X = data, Y = reference, t1 = epoch awal data, t2 = epoch akhir data
def cca(X,Y,t1,t2):

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


t = 1		# panjang waktu sinyal reference (sekond)
fs = 256	# frekuensi sampling
f = 10		# frekuensi stimulus / reference
t1 = 100*256		# sampling data dari epoch ke 0
t2 = 101*256	# sampling data berakhir di epoch ke 512

lowcutoff = 8
highcutoff = 30
data = Bandpass.Bandpass(data2,lowcutoff,highcutoff,fs)

Ref = refSignal(t,fs,f) # Reference Signal
r = cca(data,Ref,t1,t2)

print max(r)

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