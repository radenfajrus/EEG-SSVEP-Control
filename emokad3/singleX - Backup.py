import pygame, sys, thread, time, os, errno, platform
from datetime import datetime
from preprocess import *
from emotiv import Emotiv

import threading
import numpy as np
from pygame.locals import *
import multiprocessing
import testX
from stimulus_env import Env
import matplotlib.pyplot as plt

if platform.system() == "Windows":
    import socket  # Needed to prevent gevent crashing on Windows. (surfly / gevent issue #459)
import gevent

try :
    name    = sys.argv[1]
except:
    name    = 'unnamed'
    
try :
    maxtime = int(sys.argv[2])
except:
    maxtime = 10

import imp
import ctypes
import win32api

# Load the DLL manually to ensure its handler gets
# set before our handler.
basepath = imp.find_module('numpy')[1]
ctypes.CDLL(os.path.join(basepath, 'core', 'libmmd.dll'))
ctypes.CDLL(os.path.join(basepath, 'core', 'libifcoremd.dll'))

# Now set our handler for CTRL_C_EVENT. Other control event 
# types will chain to the next handler.
def handler(dwCtrlType, hook_sigint=thread.interrupt_main):
    if dwCtrlType == 0: # CTRL_C_EVENT
        hook_sigint()
        return 1 # don't chain to the next handler
    return 0 # chain to the next handler

win32api.SetConsoleCtrlHandler(handler, 1)


# Nilai data EEG
data2= np.genfromtxt('book.csv', delimiter=',')

# Pilih Rentang data --> Bandpass 6-30Hz --> Buat reference signal CCA
def getdata(t,fs):

    #f = 10      # frekuensi sinyal reference
    t1 = fs 	 #20*fs # sampling data berawal di epoch 0  
    t2 = fs+t*fs #21*fs # sampling data berakhir di epoch ke fs

    lowcutoff = 6                                        # low frequency cutoff
    highcutoff = 30                      				  # high frequency cutoff

    winsinc = testX.FIR(lowcutoff,highcutoff,fs)	 	 # Membuat koefisien FIR filter
    Ref = {
    '8.5Hz' : testX.refSignal(t,fs,8.5),                        # Reference Signal
    '10Hz'  : testX.refSignal(t,fs,10) ,
    '12Hz'  : testX.refSignal(t,fs,12) , 
    '15Hz'  : testX.refSignal(t,fs,15)  
    }

    return winsinc,Ref,t1,t2


# Multiprocessing dapat menjalankan suatu fungsi atau program pada core processor yg berbeda
# sehingga program lebih efisien berjalan secara paralel pada mesin yang bersifat multicore

# Pada Multiprocessing, ketika process dibuat, maka process tersebut akan disalin ke dalam child process
# untuk dijalankan. Variable dalam child process merupakan copyan dr Parent process, sehingga perubahan nilai
# pada variable di Parent process tidak mempengaruhi nilai variable (yg namanya sama) di child process.
# Karena itu, perpindahan nilai variable antar process harus dijembatani melalui Queue (orang ketiga)
# Process 1 (put) -> Queue.  Then Queue -> Process 2 (get)

MAXR = multiprocessing.Queue()      # Queue untuk nilai CCA dari Process penghitung CCA ke Process Display nilai CCA 
RunMain = multiprocessing.Queue()   # Queue untuk perintah dari tombol keyboard ke dalam Process penghitung CCA

pygame.init()                                      # Setting awal pygame
info        = pygame.display.Info()                # Info lebar layar monitor fullscreen
clock       = pygame.time.Clock()
global_lock = threading.Lock()

env         = Env(info.current_w, info.current_h)  
width       = info.current_w
height      = info.current_h

display     = (width, height)
screen      = pygame.display.set_mode(display, pygame.FULLSCREEN)

clr_white   = (255, 255, 255)
clr_black   = (0, 0, 0)
clr_red     = (255, 0, 0)
clr_green   = (0, 255, 0)
clr_blue    = (0, 0, 255)

clr_back    = clr_black
clr_default = clr_white

def_side    = height / 4                                               # ukuran panjang 25 % dr tinggi layar

screen.fill(clr_back)                                                  # default layar hitam

# Insert Flicker Image
img_loc     = os.path.join("images", "circle-stop.png")
img         = pygame.image.load(img_loc)                            
img         = pygame.transform.scale(img, (def_side, def_side))

# Insert Title
title_loc   = os.path.join("images", "title.png")                      # Buka file 'title.png' di folder images
title       = pygame.image.load(title_loc)               
title       = pygame.transform.scale(title, (def_side, def_side/3))    # .scale(file gambar, ukuran(lebar, tinggi))

# Multithreading digunakan untuk menjalankan 2 buah program secara paralel.
# mirip dengan multiprocessing, hanya saja threading menjalankan process
# secara paralel di dalam core processor yg tidak terpisah.

# Multithreading dilakukan untuk memisahkan proses Display flicker (class Rectangle) (running 10 fps) 
# dengan Display nilai CCA (class Background) (running 60 fps)

class Background(threading.Thread):  # Update nilai CCA 
    def __init__(self) :
        threading.Thread.__init__(self)
        self.clock      = pygame.time.Clock()
        self.last_tick  = pygame.time.get_ticks()
        self.rect2      = pygame.Surface((def_side+50, def_side/3))  # inisialisasi daerah untuk title yg ingin ditampilkan
                                                                     # Surface(ukuran(lebar,tinggi))
        self.fps        = 60    # fps untuk Background
        self.j          = 0     # variable untuk efek animasi naik-turun bar (ketika nilai CCA stabil)
        self.i          = 1     # variable untuk efek animasi naik-turun bar (ketika nilai CCA berubah)
        self.battery 	= 80
        self.color		= (0,0,0)
        self.value1 	= 0	# inisialisasi nilai awal CCA untuk Display
        self.value2 	= 0
        self.value3		= 0
        self.value4		= 0        
        self.value1a    = 100    # inisialisasi nilai awal CCA untuk Display
        self.value2a    = 90    # inisialisasi nilai awal CCA untuk Display
        self.value3a    = 80    # inisialisasi nilai awal CCA untuk Display
        self.value4a    = 70     # variable untuk penyimpanan sementaran nilai CCA
        self.screen2    = pygame.display.get_surface()               # inisialisasi daerah untuk bar yg ingin ditampilkan
                                                                     # Surface = full screen

        self.rect2.blit(title,(50,0))                                # memasukkan title ke dalam rect2. 
                                                                     # blit(file gambar, pergeseran posisi(lebar,tinggi))
        self.rect2.set_alpha(150)                                    # Transparency = 0(transparent) - 255(solid)

        self.myfont = pygame.font.SysFont("monospace", 25)           # Font
        self.myfont2 = pygame.font.SysFont("Arial", 20)           # Font
    # Multithreading .start() akan menjalankan fungsi run()
    # Run() menjalankan loop() dalam class hingga ada perintah stop dr keyboard. 
    # keyboard (event) -> ubah nilai variable pada module (stimulus_env.py) -> refresh nilai variabel dgn env.getStop()
    # Teknik tersebut dapat dilakukan karena multithreading, jadi variablenya masih bisa diakses bersama.
    # Hal tersebut tidak bisa dilakukan di multiprocessing, karena akan terbentuk 2 variable pada Parent dan child(copy)
    # yang akan berjalan terpisah.
    def run(self) :
        while True :
            if env.getStop() :
                return
            else :
                self.loop()

    def loop(self):
        # Jika hasil CCA pada process hitung CCA (multiprocessing) telah keluar dan diqueue, ganti nilai bar.
        
        if not MAXR.empty():
            #print "#"
            queue = MAXR.get()
            #print "Hasil Korelasi CCA =", queue[1]
            #self.valuea = queue
            self.value1a = int(queue[0]*100)
            self.value2a = int(queue[1]*100)
            self.value3a = int(queue[2]*100)
            self.value4a = int(queue[3]*100)
    	

        # animasi pergerakan naik-turun bar yg berfungsi sinusoidal (agar pergerakan terlihat lebih halus)
        # animasi saat nilai CCA tetap, namun bar naik-turun.
        self.j = round((np.sin(2*np.pi*self.i*1/120)+1.5)*100)
        self.k1 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value1/100)*10
        self.k2 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value2/100)*10
        self.k3 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value3/100)*10
        self.k4 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value4/100)*10
        
        # timer agar nilai bar berganti2an setiap waktu self.i mencapai nilai tertentu 
        self.i = (self.i + 1)%120   
        if ((self.i == 119)|(self.i == 59)):
            kkk = self.value1a
            self.value1a = round(self.value2a)
            self.value2a = round(self.value3a)
            self.value3a = round(self.value4a)
            self.value4a = round(kkk)
        self.battery = round(self.i / 1.2)
        self.color = (255-(self.i*2),255-(self.i*2),255-(self.i*2))
        
        # animasi pergerakan naik-turun bar yg berfungsi sinusoidal (agar pergerakan terlihat lebih halus)
        # animasi saat nilai CCA berubah.
        if self.value1 != self.value1a:
           self.value1 = (self.value1 + (self.value1a - self.value1)/7.0)
        if self.value2 != self.value2a:
           self.value2 = (self.value2 + (self.value2a - self.value2)/7.0)
        if self.value3 != self.value3a:
           self.value3 = (self.value3 + (self.value3a - self.value3)/7.0)
        if self.value4 != self.value4a:
           self.value4 = (self.value4 + (self.value4a - self.value4)/7.0)
        # default warna layar hitam
        self.screen2.fill(clr_back)

        # Memasukkan display self.rect2 (title), kedalam screen (display utama)
        screen.blit(self.rect2, ((width/10, height/10)))   # .blit(display, pergeseran posisi(lebar,tinggi))
        

        # Bar animasi naik turun
        pygame.draw.rect(self.screen2, (110,105,50), pygame.Rect(width-(def_side*1.15),def_side/2+(self.k1)+(2*def_side*(100-self.value1)/100),def_side/10,def_side*2-(self.k1)-(2*def_side*(100-self.value1)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,180), pygame.Rect(width-(def_side*0.9),def_side/2+(self.k2)+(2*def_side*(100-self.value2)/100),def_side/10,def_side*2-(self.k2)-(2*def_side*(100-self.value2)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (0,100,110), pygame.Rect(width-(def_side*0.65),def_side/2+(self.k3)+(2*def_side*(100-self.value3)/100),def_side/10,def_side*2-(self.k3)-(2*def_side*(100-self.value3)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (100,50,180), pygame.Rect(width-(def_side*0.4),def_side/2+(self.k4)+(2*def_side*(100-self.value4)/100),def_side/10,def_side*2-(self.k4)-(2*def_side*(100-self.value4)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))

        # Bar outline glow
        pygame.draw.rect(self.screen2, (100-(self.j/2.5),100-(self.j/2.5),50-(self.j/5)), pygame.Rect(width-(def_side*1.15),def_side/2,def_side/10,def_side*2), 3)
        pygame.draw.rect(self.screen2, (50-(self.j/5),50-(self.j/5),100-(self.j/2.5)), pygame.Rect(width-(def_side*0.9),def_side/2,def_side/10,def_side*2), 3)
        pygame.draw.rect(self.screen2, (0,100-(self.j/2.5),110-(self.j/2.5)), pygame.Rect(width-(def_side*0.65),def_side/2,def_side/10,def_side*2), 3)
        pygame.draw.rect(self.screen2, (100-(self.j/2.5),50-(self.j/5),125-(self.j/2)), pygame.Rect(width-(def_side*0.4),def_side/2,def_side/10,def_side*2), 3)

        # Display Nilai Persen CCA
        label_persen_85Hz = self.myfont.render(str(int(round(self.value1)))+"%", 3, (110,105,50))
        screen.blit(label_persen_85Hz, (width-(def_side*1.2),def_side*2.52))
        label_persen_10Hz = self.myfont.render(str(int(round(self.value2)))+"%", 3, (50,50,180))
        screen.blit(label_persen_10Hz, ((width-(def_side*0.95)), def_side*2.52))
        label_persen_12Hz = self.myfont.render(str(int(round(self.value3)))+"%", 3, (0,100,110))
        screen.blit(label_persen_12Hz, (width-(def_side*0.7),def_side*2.52))
        label_persen_15Hz = self.myfont.render(str(int(round(self.value4)))+"%", 3, (100,50,180))
        screen.blit(label_persen_15Hz, ((width-(def_side*0.45)), def_side*2.52))

        # Display Hz
        label_85Hz = self.myfont2.render("8.5Hz", 3, (110,105,50))
        screen.blit(label_85Hz, (width-(def_side*1.2),def_side*2.64))
        label_10Hz = self.myfont2.render("10Hz", 3, (50,50,180))
        screen.blit(label_10Hz, ((width-(def_side*0.95)), def_side*2.64))
        label_12Hz = self.myfont2.render("12Hz", 3, (0,100,110))
        screen.blit(label_12Hz, (width-(def_side*0.7),def_side*2.64))
        label_15Hz = self.myfont2.render("15Hz", 3, (100,50,180))
        screen.blit(label_15Hz, ((width-(def_side*0.45)), def_side*2.64))


        # Display Battery
        pygame.draw.rect(self.screen2, (0,85,0), pygame.Rect(width-(def_side*1.2),height-(def_side*0.4),(def_side*0.6)-((def_side*0.6)*(1-self.battery/100)),def_side*0.13))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (10,100-(self.j/2.5),0), pygame.Rect(width-(def_side*1.2),height-(def_side*0.4),def_side*0.6,def_side*0.13), 4)              
        label_battery = self.myfont.render(str(int(round(self.battery)))+"%", 3, (0,85,0))
        screen.blit(label_battery, (width-(def_side*0.5),height-(def_side*0.4)))
        

        # Display Channel Condition
        # Channel P1
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*1.2),height-(def_side*1),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*1.2),height-(def_side*1),def_side*0.15,def_side*0.1), 3)              
        label_P1 = self.myfont.render("P1", 3, (50,50,50))
        screen.blit(label_P1, (width-(def_side*1.2),height-(def_side*1.2)))
        
        # Channel O1
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*0.95),height-(def_side*0.8),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.95),height-(def_side*0.8),def_side*0.15,def_side*0.1), 3)              
        label_O1 = self.myfont.render("O1", 3, (50,50,50))
        screen.blit(label_O1, (width-(def_side*0.95),height-(def_side*1)))
        
        # Channel O2
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*0.7),height-(def_side*0.8),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.7),height-(def_side*0.8),def_side*0.15,def_side*0.1), 3)              
        label_O2 = self.myfont.render("O2", 3, (50,50,50))
        screen.blit(label_O2, (width-(def_side*0.7),height-(def_side*1)))
        
        # Channel P2
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*0.45),height-(def_side*1),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.45),height-(def_side*1),def_side*0.15,def_side*0.1), 3)              
        label_P2 = self.myfont.render("P2", 3, (50,50,50))
        screen.blit(label_P2, (width-(def_side*0.45),height-(def_side*1.2)))
        
        # Channel Ground Left
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*1.2),height-(def_side*0.6),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*1.2),height-(def_side*0.6),def_side*0.15,def_side*0.1), 3)              
        label_GNDL = self.myfont.render("GndL", 3, (50,50,50))
        screen.blit(label_GNDL, (width-(def_side*1.3),height-(def_side*0.8)))
        
        # Channel Ground Right
        pygame.draw.rect(self.screen2, self.color, pygame.Rect(width-(def_side*0.45),height-(def_side*0.6),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.45),height-(def_side*0.6),def_side*0.15,def_side*0.1), 3)              
        label_GNDR = self.myfont.render("GndR", 3, (50,50,50))
        screen.blit(label_GNDR, (width-(def_side*0.5),height-(def_side*0.8)))
       

        # Update display, (1). Bar, (2). Title 
        global_lock.acquire()
        try:        
            pygame.display.update(width*3/4,0,width,height)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
            pygame.display.update(0,0,width/2,height/4)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
        
        finally:
            global_lock.release()

        # wait process pygame 20 ms
        pygame.time.wait(20)        


class Rectangle(threading.Thread):              # Update Display Filcker (Nyala Mati sesuai frekuensi flicker)
    def __init__(self, fps) :
        threading.Thread.__init__(self)
        self.clock      = pygame.time.Clock()
        self.last_tick  = pygame.time.get_ticks()
        self.rect       = pygame.Surface((def_side, def_side))
        self.up         = 0
        self.fps        = fps
        self.delay      = 1000 / (fps * 2)      # periode terang = 1/(2*fps) sekond, periode gelap = 1/(2*fps) sekond

    def run(self) :
        while True :
            if env.getStop() :
                return
            else :
                self.loop()

    def loop(self) :
        if (env.getRun()) :
            if (self.up) :
                self.rect.fill(clr_default)
                self.rect.blit(img, (0, 0))

                self.up  = 0
            else :
                self.rect.fill(clr_back)

                self.up  = 1
        else :
            self.rect.fill(clr_default)
            self.rect.blit(img, (0, 0))

        # self.rect.set_alpha(self.alpha)
        global_lock.acquire()
        try:        
            screen.blit(self.rect, ((width - def_side) / 2 , (height - def_side) / 2 ))
            pygame.display.update((width - def_side) / 2 , (height - def_side) / 2 ,(width - def_side) / 2 +def_side, (height - def_side) / 2 +def_side)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
        finally:
            global_lock.release()

        pygame.time.wait(self.delay)
        #pygame.display.update(0,0,width,height)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))


# Process Hitung CCA
def Main(winsinc,Ref,t1,t2,timeout,headset): 

    fsa = 128
    dataa,data2a = range(fsa),range(fsa)
    head = 0
    second      = 0
    first       = -1
    
    start_time      = int(round(time.time() * 1000))
    print RunMain.empty()
    # Mendeteksi Inputan Keyboard
    while RunMain.empty() :
        #print RunMain.empty()
        #print headset.packets.empty()
        time_now    = int(round(time.time() * 1000)) - start_time 
        print "2"
        packetx      = headset.packets
        print packetx

        if not headset.packets.empty():
            print "3"
            packet      = headset.packets.get()
            # output.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (time.time(), packet.counter, packet.F3[0], packet.FC5[0], packet.AF3[0], packet.F7[0], packet.T7[0], packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.T8[0], packet.F8[0], packet.AF4[0], packet.FC6[0], packet.F4[0], packet.gyro_x, packet.gyro_y))
            # output.write("%i,%s,%s,%s,%s,%s,%s,%s\n" % (time_now, packet.counter, packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.gyro_x, packet.gyro_y))
            #Q.put(packet.battery)
            print packet.battery
            if packet.counter == 128:
                #print time_now
                second = second + 1
                start_time      = int(round(time.time() * 1000))

                timing     = time.time()*1000.0 - timeout

                while tail != head :
                    #print "@"
                    data2a[count] = dataa[tail-1]
                    tail = (tail + 1)%fs
                    count = count + 1
                data2a[count] = dataa[(tail-1)%fsa]  
                #print timing

                if (timing > 4000):
                    ms = time.time()*1000.0
                    data = testX.Bandpass(data2a, winsinc) # Bandpass menggunakan FIR windowed sinc (hamming weigth)    
                    r = testX.cca(data,Ref,t1,t2)#(B,C,0,5)#
                    print max(r)
                    MAXR.put(max(r))
                    timeout = time.time()*1000.0  
                    print packet.battery
                    print "Waktu Hitung (ms) =", timeout - ms
            else :
                dataa[head] = packet.counter
                head = (head + 1) % fsa
                tail = (head + 1) % fsa
                count = 0                  
    print "6"
    packetx.close()
    RunMain.get()
    RunMain.close()        


def eventLoop(winsinc2):
    for event in pygame.event.get():
        if event.type == QUIT :
            RunMain.put("1")            # Beri Signal Queue kedalam Process hitung CCA
            env.killStop()              # stop Process TEST.start()
            pygame.quit()               # Quit pygame
            sys.exit()                  # exit program
        elif event.type == KEYDOWN :
            # tombol ESC
            if event.key == K_ESCAPE :
                RunMain.put("1")
                env.killStop()
                pygame.quit()
                sys.exit()
            # tombol panah bawah                
            if event.key == K_SPACE :
                env.changeRun()         # Halt pygame
        elif event.type == USEREVENT + 1:
                RunMain.put("1")
                env.killStop()
                pygame.quit()
                sys.exit()
        elif winsinc2 == False:
                RunMain.put("1")
                env.killStop()
                pygame.quit()
                sys.exit()                

#global headset
def run() :

    FreqFlicker = 10

    winsinc,Ref,t1,t2 = getdata(t,fs)                # Pengondisian Sinyal data
    winsinc2 = bool(max(winsinc))

    #pygame.time.set_timer(USEREVENT + 1,8000) # Timer Interrupt

    # Start Multithreading
    background = Background()                 # menjalankan init() Class Background 
    forward = Rectangle(FreqFlicker)          # menjalankan init() Class Rectangle 
    forward.start()
    background.start()

    #print "2"
    # Start Multiprocessing
    
    TES = threading.Thread(target=Main,args=(winsinc,Ref,t1,t2,timeout,headset))
    TES.daemon = True
    TES.start()
    print "4"
    while True :
        eventLoop(winsinc2)                      	 # Loop Utama
        clock.tick(60)                  	 # limit frame menjadi 60 fps

if __name__ == "__main__":
    #TES = process(processes=4)
    FreqFlicker = 10
    t = 1        # panjang waktu sinyal reference (sekond)
    fs = 128     # frekuensi sampling

    #pygame.time.set_timer(USEREVENT + 1,6000) # Timer Interrupt

    background = Background()                 # menjalankan init() Class Background 
    forward = Rectangle(FreqFlicker)          # menjalankan init() Class Rectangle 
    forward.start()
    background.start()

    headset = Emotiv()
    gevent.spawn(headset.setup)
    gevent.sleep(0)

    winsinc,Ref,t1,t2 = getdata(t,fs)                # Pengondisian Sinyal data
    winsinc2 = bool(max(winsinc))
    # print winsinc
    # print winsinc.shape

    data        = {
        'second'    : [],
        'counter'   : [],
        'F3'        : [],
        'FC5'       : [],
        'AF3'       : [],
        'F7'        : [],
        'T7'        : [],
        'P7'        : [],
        'O1'        : [],
        'O2'        : [],
        'P8'        : [],
        'T8'        : [],
        'F8'        : [],
        'AF4'       : [],
        'FC6'       : [],
        'F4'        : []
    }
    # output.write("SECOND,COUNTER,F3,FC5,AF3,F7,T7,P7,O1,O2,P8,T8,F8,AF4,FC6,F4,GYRO_X,GYRO_Y\n")
    fsa 		 = 128*2
    dataa,data2a = range(fsa),range(fsa)
    head 		 = 0
    second       = 0
    first        = -1
    D 		 	 = 0
    start_time   = int(round(time.time() * 1000))
    timeout      = time.time()*1000.0

    # print RunMain.empty()
    # Mendeteksi Inputan Keyboard
    g = 0
    try:
        while RunMain.empty() :
            eventLoop(winsinc2)
            # print RunMain.empty()
            # print headset.packets.empty()
            time_now    = int(round(time.time() * 1000)) - start_time 
            # print headset.packets_received
            while bool(headset.packets_received-g):
            	g = headset.packets_received
            	packet      = headset.dequeue()
                # print "3"
                # output.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (time.time(), packet.counter, packet.F3[0], packet.FC5[0], packet.AF3[0], packet.F7[0], packet.T7[0], packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.T8[0], packet.F8[0], packet.AF4[0], packet.FC6[0], packet.F4[0], packet.gyro_x, packet.gyro_y))
                # output.write("%i,%s,%s,%s,%s,%s,%s,%s\n" % (time_now, packet.counter, packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.gyro_x, packet.gyro_y))
                # Q.put(packet.battery)
                # print packet.counter
                
                if packet.counter == 128:
	                #print time_now
                    second = (second + 1)%3
                    start_time      = int(round(time.time() * 1000))

                    timing     = time.time()*1000.0 - timeout
 
                    # print timing

                    if (second == 2):
                        
                        ms = time.time()*1000.0
                        data = testX.Bandpass(np.array([data2a]), winsinc) # Bandpass menggunakan FIR windowed sinc (hamming weigth)    
                        r = testX.cca(data,Ref,t1,t2)#(B,C,0,5)#
                        print r
                        MAXR.put(r)
                        timeout = time.time()*1000.0  
                        # print packet.battery
                        print "Waktu Hitung (ms) =", timeout - ms
                else :
                    dataa[head] = packet.counter
                    head = (head + 1) % fsa
                    tail = (head + 1) % fsa
                    count = 0 

                    while tail != head :
                        # print "@"
                        data2a[count] = dataa[tail-1]
                        tail = (tail + 1)%fsa
                        count = count + 1
                    data2a[count] = dataa[(tail-1)%fsa] 
        #print "#print "6"
        RunMain.get()
        RunMain.close()        

    except KeyboardInterrupt:
        headset.close()
        #os.system('clear')
    finally:
        headset.close()
        #os.system('clear')
    
