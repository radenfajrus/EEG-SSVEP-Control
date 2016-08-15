import testX, time
from numpy import genfromtxt as np 

data2= np('book.csv', delimiter=',')

def Main():
	ms = time.time()*1000.0

	#data2= np.genfromtxt('book.csv', delimiter=',')


	t = 1       # panjang waktu sinyal reference (sekond)
	fs = 256    # frekuensi sampling
	f = 8.5     # frekusampling data dari epoch ke 0
	t1 = 20*256 # sampling data berawal di epoch 0  
	t2 = 21*256 # sampling data berakhir di epoch ke 255

	lowcutoff = 8
	highcutoff = 30
	winsinc = testX.FIR(lowcutoff,highcutoff,fs)	 	 # Membuat koefisien FIR filter
	Ref = {
	'8.5Hz' : testX.refSignal(t,fs,8.5),                        # Reference Signal
	'10Hz'  : testX.refSignal(t,fs,10) ,
	'12Hz'  : testX.refSignal(t,fs,12) , 
	'15Hz'  : testX.refSignal(t,fs,15)  
	}
	data = testX.Bandpass(data2,winsinc)

	ms = time.time()*1000.0
	r = testX.cca(data,Ref,t1,t2)#(B,C,0,5)#
	print "Hasil Korelasi CCA =", max(r)
	print "Waktu Hitung (ms) =", time.time()*1000.0 - ms

Main()