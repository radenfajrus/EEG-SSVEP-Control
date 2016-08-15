import pygame, sys, thread, time, os, errno, platform, string
sys.path.insert(0, '..')

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

from pgu import gui

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
# data2= np.genfromtxt('book.csv', delimiter=',')

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
Q = multiprocessing.Queue()

pygame.init()                                      # Setting awal pygame
pygame.font.init()								   # Setting awal pygame font
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
# title_loc   = os.path.join("images", "title.png")                      # Buka file 'title.png' di folder images
# title       = pygame.image.load(title_loc)               
# title       = pygame.transform.scale(title, (def_side, def_side/3))    # .scale(file gambar, ukuran(lebar, tinggi))

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
        # self.rect2      = pygame.Surface((def_side+50, def_side/3))  # inisialisasi daerah untuk title yg ingin ditampilkan
                                                                     # Surface(ukuran(lebar,tinggi))
        self.fps        = 60    # fps untuk Background
        self.j          = 0     # variable untuk efek animasi naik-turun bar (ketika nilai CCA stabil)
        self.i          = 1     # variable untuk efek animasi naik-turun bar (ketika nilai CCA berubah)
        self.n 			= 0     
        self.battery 	= 100
        self.colorP1 = self.colorO1 = self.colorO2 = self.colorP2	= (0,255,0)
        self.colorGndL 			    = self.colorGndR 				= (0,255,0)
        self.value1  = self.value2  = self.value3  = self.value4	= 30 		# inisialisasi nilai awal CCA untuk Display
        self.value1a = self.value2a = self.value3a = self.value4a   = 10    	# inisialisasi nilai awal CCA untuk Display
        self.screen2    = pygame.display.get_surface()               # inisialisasi daerah untuk bar yg ingin ditampilkan
                                                                     # Surface = full screen

                                                          			 # blit(file gambar, pergeseran posisi(lebar,tinggi))
        #self.rect2.set_alpha(150)                                   # Transparency = 0(transparent) - 255(solid)
        #app.run(e)

        self.myfont = pygame.font.SysFont("monospace", def_side/8)           # Font
        self.myfont2 = pygame.font.SysFont("Arial", def_side/9)           # Font
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
                if (not env.getSerius()) :
                    self.loop()
                #else :
  


    def loop(self):
        # Jika hasil CCA pada process hitung CCA (multiprocessing) telah keluar dan diqueue, ganti nilai bar.
        
        if not MAXR.empty():
            #print "#"
            queue = MAXR.get()
            
            #print "Hasil Korelasi CCA =", queue[1]
            #self.valuea = queue
            self.value1a = int(max(queue[0])*100)
            self.value2a = int(max(queue[1])*100)
            self.value3a = int(max(queue[2])*100)
            self.value4a = int(max(queue[3])*100)
        if not Q.empty():
            queue2 = Q.get()
            #print queue2

            self.battery = int(queue2[0])
            #print self.battery
            self.colorP1 = (0,queue2[1],0)
            self.colorO1 = (0,queue2[2],0)
            self.colorO2 = (0,queue2[3],0)
            self.colorP2 = (0,queue2[4],0)
            #self.colorGndL = (255-(self.i*2),255-(self.i*2),255-(self.i*2))
            #self.colorGndR = (255-(self.i*2),255-(self.i*2),255-(self.i*2))

        # animasi pergerakan naik-turun bar yg berfungsi sinusoidal (agar pergerakan terlihat lebih halus)
        # animasi saat nilai CCA tetap, namun bar naik-turun.
        self.j = round((np.sin(2*np.pi*self.i*1/120)+1.5)*100)
        self.k1 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value1/100)*10
        self.k2 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value2/100)*10
        self.k3 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value3/100)*10
        self.k4 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value4/100)*10
        
        # timer agar nilai bar berganti2an setiap waktu self.i mencapai nilai tertentu 
        self.i = (self.i + 1)%120   
        #if ((self.i == 119)|(self.i == 59)):
            #kkk = self.value1a
            #self.value1a = round(self.value2a)
            #self.value2a = round(self.value3a)
            #self.value3a = round(self.value4a)
            #self.value4a = round(kkk)

        self.n = self.n^1
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
        # screen.blit(self.rect2, ((width/10, height/10)))   # .blit(display, pergeseran posisi(lebar,tinggi))

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
        pygame.draw.rect(self.screen2, (0,85,0), pygame.Rect(width-(def_side*1.2),height-(def_side*0.4),(def_side*0.6)-((def_side*0.6)*(1-self.battery/100.0)),def_side*0.13))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (10,100-(self.j/2.5),0), pygame.Rect(width-(def_side*1.2),height-(def_side*0.4),def_side*0.6,def_side*0.13), 4)              
        label_battery = self.myfont.render(str(int(round(self.battery)))+"%", 3, (0,85,0))
        screen.blit(label_battery, (width-(def_side*0.5),height-(def_side*0.4)))
        
        # Display Channel Condition
        # Channel P1
        pygame.draw.rect(self.screen2, (self.colorP1), pygame.Rect(width-(def_side*1.2),height-(def_side*1),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*1.2),height-(def_side*1),def_side*0.15,def_side*0.1), 3)              
        label_P1 = self.myfont.render("P1", 3, (50,50,50))
        screen.blit(label_P1, (width-(def_side*1.2),height-(def_side*1.2)))
        
        # Channel O1
        pygame.draw.rect(self.screen2, self.colorO1, pygame.Rect(width-(def_side*0.95),height-(def_side*0.8),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.95),height-(def_side*0.8),def_side*0.15,def_side*0.1), 3)              
        label_O1 = self.myfont.render("O1", 3, (50,50,50))
        screen.blit(label_O1, (width-(def_side*0.95),height-(def_side*1)))
        
        # Channel O2
        pygame.draw.rect(self.screen2, self.colorO2, pygame.Rect(width-(def_side*0.7),height-(def_side*0.8),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.7),height-(def_side*0.8),def_side*0.15,def_side*0.1), 3)              
        label_O2 = self.myfont.render("O2", 3, (50,50,50))
        screen.blit(label_O2, (width-(def_side*0.7),height-(def_side*1)))
        
        # Channel P2
        pygame.draw.rect(self.screen2, self.colorP2, pygame.Rect(width-(def_side*0.45),height-(def_side*1),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.45),height-(def_side*1),def_side*0.15,def_side*0.1), 3)              
        label_P2 = self.myfont.render("P2", 3, (50,50,50))
        screen.blit(label_P2, (width-(def_side*0.45),height-(def_side*1.2)))
        
        # Channel Ground Left
        pygame.draw.rect(self.screen2, self.colorGndL, pygame.Rect(width-(def_side*1.2),height-(def_side*0.6),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*1.2),height-(def_side*0.6),def_side*0.15,def_side*0.1), 3)              
        label_GNDL = self.myfont.render("GndL", 3, (50,50,50))
        screen.blit(label_GNDL, (width-(def_side*1.3),height-(def_side*0.8)))
        
        # Channel Ground Right
        pygame.draw.rect(self.screen2, self.colorGndR, pygame.Rect(width-(def_side*0.45),height-(def_side*0.6),def_side*0.15,def_side*0.1))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (50,50,50), pygame.Rect(width-(def_side*0.45),height-(def_side*0.6),def_side*0.15,def_side*0.1), 3)              
        label_GNDR = self.myfont.render("GndR", 3, (50,50,50))
        screen.blit(label_GNDR, (width-(def_side*0.5),height-(def_side*0.8)))

        # Status Save
        label_save = self.myfont.render("Save > ", 3, (0,5,60))
        screen.blit(label_save, (width-(def_side*1.2),height-(def_side*0.2)))     
        if (env.getSave()) :
            label_save1 = self.myfont.render(" True ", 3, (0,5,60))
            screen.blit(label_save1, (width-(def_side*0.7),height-(def_side*0.2)))    
        else :
            label_save2 = self.myfont.render(" False", 3, (40,5,0))
            screen.blit(label_save2, (width-(def_side*0.7),height-(def_side*0.2)))   

        # Update display, (1). Bar, (2). Title 
        global_lock.acquire()
        try:        
            pygame.display.update(width*0.8,0,width*0.2,height)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
            #pygame.display.update(0,height*3/4,width*3/4,0)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
        finally:
            global_lock.release()

        # wait process pygame 20 ms
        pygame.time.wait(1000/(20))  

class Rectangle2(threading.Thread):              # Update Display Filcker (Nyala Mati sesuai frekuensi flicker)
    def __init__(self, fps) :
        threading.Thread.__init__(self)
        self.clock      = pygame.time.Clock()
        self.last_tick  = pygame.time.get_ticks()
        self.rect       = pygame.Surface((def_side, def_side))

        self.up         = 0
        self.fps        = fps
        self.delay      = 1000 / (fps * 2)      # periode terang = 1/(2*fps) sekond, periode gelap = 1/(2*fps) sekond
        self.myfont2	= pygame.font.SysFont("Arial", def_side/9)

    def run(self) :
        while True :
            if env.getStop() :
                return
            else :
                if (env.getState() == 1) and (not env.getSerius()):
                    self.loop()
                #else:


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
        screen.blit(self.rect, ((width - (def_side*2)) / 2 , (height - def_side) / 2 ))
        
        label_G2 = self.myfont2.render("10 Hz  Flicker", 3, (50,0,50))                
        screen.blit(label_G2, ((def_side)*0.2,(height-(def_side*0.2))))
                   
        global_lock.acquire()
        try:    
            pygame.display.update(0,height*4/5,width*1/5,height/5)     
            pygame.display.update((width - (def_side*2)) / 2 , (height - def_side) / 2 ,def_side, def_side)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
        finally:
            global_lock.release()

        pygame.time.wait(self.delay)
        #pygame.display.update(0,0,width,height)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))


avail_state = ['stop', 'left', 'right', 'forward']
class Rectangle(threading.Thread):
    def __init__(self, freq, pos, img, name='Unnamed', ) :
        threading.Thread.__init__(self)
        self.clock      = pygame.time.Clock()
        self.surface    = pygame.Surface(env.getRectSize())
        self.up         = 0
        self.pos1 		= pos[0]
        self.pos2		= pos[1]
        self.image      = img
        self.delay      = 1000 / (freq * 2)      # periode terang = 1/(2*fps) sekond, periode gelap = 1/(2*fps) sekond
        self.myfont2	= pygame.font.SysFont("Arial", def_side/9)

    def run(self) :
        while True :
            if env.getStop() :              
                return
            else :
                if (env.getState() == 0) and (not env.getSerius()):
                    
                    self.pos        = (self.pos1-120,self.pos2-70)
                    self.rect       = self.pos + env.getRectSize()
                    
                    label_G = self.myfont2.render("4 side Flicker", 3, (50,0,50))
                    screen.blit(label_G, ((def_side)*0.2,(height-(def_side*0.2))))
                    self.loop()

                elif (env.getState() == 0) and (env.getSerius()):
                    
                    self.pos        = (self.pos1,self.pos2) 
                    self.rect       = self.pos + env.getRectSize()
                    self.loop()

    def loop(self) :
        self.clock.tick()

        if (env.getRun()) :
            if (self.up) :
                self.up  = 0
                self.surface.fill(clr_default)
                if self.image is not None : self.surface.blit(self.image, (0, 0))
            else :
                self.up  = 1
                self.surface.fill(clr_back)
        else :
            self.up  = 0
            self.surface.fill(clr_default)
            if self.image is not None : self.surface.blit(self.image, (0, 0))

        screen.blit(self.surface, self.pos)

        global_lock.acquire()
        try:
            pygame.display.update(0,height*4/5,width*1/5,height/5)
            pygame.display.update(self.rect)
        finally:
            global_lock.release()
        # self.count += 1
        # print self.name + ' => ' + str(self.count) + ' => ' + str(self.clock.get_time()) + " => " + str(self.clock.get_fps()) + " fps => " + str((pygame.time.get_ticks() - self.init_tick) / 1000)
        # print self.name
        pygame.time.wait(self.delay)

def eventLoop(winsinc2,filename,folder,maxtime,output):
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
            if event.key == K_F5 :
                env.changeSerius()
                screen.fill(clr_back)
                pygame.display.update()
                pygame.time.wait(50)   
                if env.getSerius() :
                    #print filename
                    if env.getSave() : 
                        fullpath    = os.path.join(folder, filename)
                        if not os.path.exists(os.path.dirname(fullpath)):
                            try:
                                os.makedirs(os.path.dirname(fullpath))
                            except OSError as exc: # Guard against race condition
                                if exc.errno != errno.EEXIST:
                                    raise
                        output   = open(os.path.join(folder, filename), 'w')            
                    if not (env.getRun()) : 
                        env.changeRun()         # Halt pygame  

                elif not env.getSerius() :
                    env.changeRun()
                    filename    = datetime.now().strftime('%H%M%S') + "_" + "" + "_" + str(maxtime) + ".csv" 
                    return filename,output

                # tombol panah bawah  
            if not env.getSerius() :                  
                if event.key == K_TAB :
                    env.changeRun()         # Halt pygame
                if event.key == K_F1 :
                    #print filename,folder
                    filename = ask(screen,"Insert Here ",filename,folder)
                    return filename,output 
                if event.key == K_F2 :
                    env.changeSave()                    
                if event.key == K_RIGHT :
                    env.addState()              # stop Process TEST.start()
                    screen.fill(clr_back)
                    pygame.display.update(0,0,width*3/4,height*9/10)
                    pygame.time.wait(50)
                if event.key == K_LEFT :
                    env.subState()              # stop Process TEST.start()    
                    screen.fill(clr_back)
                    pygame.display.update(0,0,width*3/4,height*9/10)
                    pygame.time.wait(50)
        # Halt pygame        
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
    return filename,output  

def get_key():
    while 1:
        event = pygame.event.poll()
        if event.type == KEYDOWN:
          return event.key
        else:
            pass

def display_box(screen, message):
    "Print a message in a box in the middle of the screen"
    fontobject = pygame.font.Font(None,18)
    myfont = pygame.font.SysFont("monospace", def_side/8)           # Font
    myfont2 = pygame.font.SysFont("Arial", def_side/9)              # Font
    #"Output File :"
    pygame.draw.rect(screen, (50,0,70), pygame.Rect((def_side)*3.5,(height-(def_side*0.2)),def_side*1.7,def_side*0.15), 2)              
    #label_1 = myfont2.render(message, 3, (50,50,70))
    #screen.blit(label_1, ((def_side)*1.6,(height-(def_side*0.2))))

    if len(message) != 0:
        label_2 = myfont2.render("<Enter>", 3, (0,5,70))
        screen.blit(label_2, ((def_side)*4.8,(height-(def_side*0.2))))  
        label_1 = myfont2.render(message, 3, (50,50,70))
        screen.blit(label_1, ((def_side)*1.6,(height-(def_side*0.2))))  
    
    global_lock.acquire()
    try:        
        pygame.display.update(0,height*9/10,width*3/4,height/10)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))
    finally:
        global_lock.release()

def ask(screen, question,filename,folder):
    current_string = []
    display_box(screen, question + ":    "+ folder+ "     " + string.join(current_string,""))
    while 1:
        inkey = get_key()
        if inkey == K_BACKSPACE:
            current_string = current_string[0:-1]
        elif inkey == K_RETURN:
            if len(current_string) == 0 :
                display_box(screen, "Output File "+ ":    "+ folder+ "     " + filename + " (..Default..)")
            else :
            	display_box(screen, "Output File "+ ":    "+ folder+ "     " + string.join(current_string,""))
            break
        elif (inkey == K_MINUS) or (inkey == K_SPACE):
            current_string.append("_")
        elif inkey <= 127:
            current_string.append(chr(inkey))
        display_box(screen, question + ":    "+ folder+ "     " + string.join(current_string,""))
    return string.join(current_string,"")

if __name__ == "__main__":
    
    folder      = os.path.dirname(os.path.abspath(__file__))+'\\data\\'
    name 		= ""
    filename    = datetime.now().strftime('%H%M%S') + "_" + name + "_" + str(maxtime) + ".csv"
    output      = 0           
                    
    FreqFlicker = 10
    t = 1        # panjang waktu sinyal reference (sekond)
    fs = 128     # frekuensi sampling

    #pygame.time.set_timer(USEREVENT + 1,6000) # Timer Interrupt

    headset = Emotiv()
    gevent.spawn(headset.setup)
    gevent.sleep(0)

    for val in avail_state :
        rect    = Rectangle(env.getRectFreq(val), (env.getRectPos(val)[0],env.getRectPos(val)[1]), env.getRectIMG(val), val)
        rect.start()

    background = Background()                 # menjalankan init() Class Background 
    background.start()
    rectangle2 = Rectangle2(10)                 # menjalankan init() Class Background 
    rectangle2.start()

    winsinc,Ref,t1,t2 = getdata(t,fs)                # Pengondisian Sinyal data
    winsinc2 = bool(max(winsinc))
    # print winsinc
    # print winsinc.shape

    #app.init(c)
    #screen.fill((0,0,0))
    #app.paint()

    #self.screen2.blit(app,(0,0))   
    # memasukkan title ke dalam menu. 
    pygame.display.flip()   
    dataW        = {
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
    fsa 		 = fs*2
    dataP1  = dataO1  = dataO2  = dataP2  = range(fsa)
    data2P1 = data2O1 = data2O2 = data2P2 = range(fsa)
    head 		 = 0
    second       = 0
    first        = -1
    D 		 	 = 0
    point 		 = 0
    start_time   = int(round(time.time() * 1000))
    timeout      = time.time()*1000.0
    timeout2 	 = start_time

    # print RunMain.empty()
    # Mendeteksi Inputan Keyboard
    g = 0
    try:
        while RunMain.empty() :

            #print filename
            filename,output = eventLoop(winsinc2,filename,folder,maxtime,output)
            
            # print RunMain.empty()
            # print headset.packets.empty()
             
            # print headset.packets_received
            while bool(headset.packets_received-g):
                g = headset.packets_received
                packet      = headset.dequeue()
                time_now    = int(round(time.time() * 1000)) - start_time
                print "!"
                if packet.counter == 128:
	                #print time_now
                    second = (second + 1)%3
                    # start_time      = int(round(time.time() * 1000))
                    timing     = time.time()*1000.0 - timeout
                    # print timing

                    if (second == 2):
                        ms = time.time()*1000.0
                        # print np.array([data2P1,data2P2]).shape
                        data = testX.Bandpass(np.array([data2P1,data2O1,data2O2,data2P2]), winsinc) # Bandpass menggunakan FIR windowed sinc (hamming weigth)    
                        r = testX.cca(data,Ref,t1,t2)#(B,C,0,5)#
                        #print r
                        MAXR.put(r)
                        timeout = time.time()*1000.0  
                        # print packet.battery
                        print "Waktu Hitung (ms) =", timeout - ms

                else :
                    #print "0"
                    if env.getSave() and env.getSerius() :
                        #print "1"
                        output.write("%s,%s,%s,%s,%s,%s,%s,%s\n" % (point, time_now, time_now-timeout2, packet.counter, packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0]))

                        dataW['second'].append(time_now)
                        dataW['counter'].append(packet.counter)
                        dataW['P7'].append(packet.P7[0])
                        dataW['O1'].append(packet.O1[0])
                        dataW['O2'].append(packet.O2[0])
                        dataW['P8'].append(packet.P8[0])
                        point = point + 1
                        timeout2 = time_now
                    if (packet.counter == 127):
                        Q.put(np.array([packet.battery,packet.sensors['P7']['quality'],packet.sensors['O1']['quality'],packet.sensors['O2']['quality'],packet.sensors['P8']['quality']]))

                    dataP1[head] = packet.sensors['P7']['value']
                    dataO1[head] = packet.sensors['O1']['value']
                    dataO2[head] = packet.sensors['O2']['value']
                    dataP2[head] = packet.sensors['P8']['value']
                    head = (head + 1) % fsa
                    tail = (head + 1) % fsa
                    count = 0 
                    #print packet.battery

                    while tail != head :
                        # print "@"
                        data2P1[count] = dataP1[tail-1]
                        data2O1[count] = dataO1[tail-1]
                        data2O2[count] = dataO2[tail-1]
                        data2P2[count] = dataP2[tail-1]
                        tail = (tail + 1)%fsa
                        count = count + 1
                    data2P1[count] = dataP1[(tail-1)]#%fsa]
                    data2O1[count] = dataO1[(tail-1)]
                    data2O2[count] = dataO2[(tail-1)]
                    data2P2[count] = dataP2[(tail-1)] 

        #print "#print "6"
        RunMain.get()
        RunMain.close()        

    except KeyboardInterrupt:
        headset.close()
        #os.system('clear')
    finally:
        headset.close()
        #os.system('clear')
    
