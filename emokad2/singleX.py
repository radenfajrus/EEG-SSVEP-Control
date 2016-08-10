import pygame, sys, thread, time, os
import threading
import numpy as np
from pygame.locals import *
import multiprocessing
import testX
from stimulus_env import Env


# Nilai data EEG
data2= np.genfromtxt('book.csv', delimiter=',')

# Pilih Rentang data --> Bandpass 6-30Hz --> Buat reference signal CCA
def getdata():
    t = 1       # panjang waktu sinyal reference (sekond)
    fs = 256    # frekuensi sampling
    f = 8.5     # frekuensi sinyal reference
    t1 = 20*256 # sampling data berawal di epoch 0  
    t2 = 21*256 # sampling data berakhir di epoch ke 255

    lowcutoff = 6                                        # low frequency cutoff
    highcutoff = 30                                      # high frequency cutoff
    data = testX.Bandpass(data2,lowcutoff,highcutoff,fs) # Bandpass menggunakan FIR windowed sinc (hamming weigth)
    Ref = testX.refSignal(t,fs,f)                        # Reference Signal
    return data,Ref,t1,t2


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
        self.valuea     = 10    # inisialisasi nilai awal CCA untuk Display
        self.value2a    = 90    # inisialisasi nilai awal CCA untuk Display
        self.value      = 0     # variable untuk penyimpanan sementaran nilai CCA
        self.value2     = 0     # variable untuk penyimpanan sementaran nilai CCA
        self.screen2    = pygame.display.get_surface()               # inisialisasi daerah untuk bar yg ingin ditampilkan
                                                                     # Surface = full screen

        self.rect2.blit(title,(50,0))                                # memasukkan title ke dalam rect2. 
                                                                     # blit(file gambar, pergeseran posisi(lebar,tinggi))
        self.rect2.set_alpha(150)                                    # Transparency = 0(transparent) - 255(solid)

        self.myfont = pygame.font.SysFont("monospace", 25)           # Font

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
            queue = MAXR.get()
            print "Hasil Korelasi CCA =", queue
            self.valuea = queue*100

        # animasi pergerakan naik-turun bar yg berfungsi sinusoidal (agar pergerakan terlihat lebih halus)
        # animasi saat nilai CCA tetap, namun bar naik-turun.
        if self.value != self.valuea:
            self.value = (self.value + (self.valuea - self.value)/7.0)
        if self.value2 != self.value2a:
            self.value2 = (self.value2 + (self.value2a - self.value2)/7.0)

        # animasi pergerakan naik-turun bar yg berfungsi sinusoidal (agar pergerakan terlihat lebih halus)
        # animasi saat nilai CCA berubah.
        self.j = round((np.sin(2*np.pi*self.i*1/120)+1.5)*100)
        self.k1 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value/100)*10
        self.k2 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value2/100)*10
        
        # timer agar nilai bar berganti2an setiap waktu self.i mencapai nilai tertentu 
        self.i = (self.i + 1)%120   
        if (self.i == 119)|(self.i == 59):
            self.value2a = round(self.value)
            self.valuea = round(self.value2)

        # default warna layar hitam
        self.screen2.fill(clr_back)

        # Memasukkan display self.rect2 (title), kedalam screen (display utama)
        screen.blit(self.rect2, ((width/10, height/10)))   # .blit(display, pergeseran posisi(lebar,tinggi))
        

        # Bar animasi naik turun
        pygame.draw.rect(self.screen2, (0,105,0), pygame.Rect(width-(def_side*1.3),def_side+(self.k1)+(2*def_side*(100-self.value)/100),def_side/10,def_side*2-(self.k1)-(2*def_side*(100-self.value)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))
        pygame.draw.rect(self.screen2, (0,0,130), pygame.Rect((width-def_side),def_side+(self.k2)+(2*def_side*(100-self.value2)/100),def_side/10,def_side*2-(self.k2)-(2*def_side*(100-self.value2)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))

        # Bar outline glow
        pygame.draw.rect(self.screen2, (0,125-(self.j/2),0), pygame.Rect(width-(def_side*1.3),def_side,def_side/10,def_side*2), 3)
        pygame.draw.rect(self.screen2, (0,0,125-(self.j/2)), pygame.Rect((width-def_side),def_side,def_side/10,def_side*2), 3)

        # Display Nilai Persen CCA
        label_persen_ijo = self.myfont.render(str(int(round(self.value)))+"%", 3, (0,155,0))
        screen.blit(label_persen_ijo, (width-(def_side*1.35),def_side*3.05))
        label_persen_biru = self.myfont.render(str(int(round(self.value2)))+"%", 3, (0,0,155))
        screen.blit(label_persen_biru, ((width-(def_side*1.05)), def_side*3.05))

        # Display Hz
        label_ijo = self.myfont.render("10 Hz", 3, (0,155,0))
        screen.blit(label_ijo, (width-(def_side*1.4),def_side*3.18))
        label_biru = self.myfont.render("12 Hz", 3, (0,0,155))
        screen.blit(label_biru, ((width-(def_side*1.08)), def_side*3.18))

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
def Main(data,Ref,t1,t2,timeout): 
    while RunMain.empty():
        timing     = time.time()*1000.0 - timeout
        if (timing > 2000):
            ms = time.time()*1000.0    
            r = testX.cca(data,Ref,t1,t2)#(B,C,0,5)#
            #print max(r)
            MAXR.put(max(r))
            timeout = time.time()*1000.0  
            print "Waktu Hitung (ms) =", timeout - ms
    RunMain.get()
    RunMain.close()

# Mendeteksi Inputan Keyboard
def eventLoop() :
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

def run() :

    fps = 10
    
    data,Ref,t1,t2 = getdata()                # Pengondisian Sinyal data

    pygame.time.set_timer(USEREVENT + 1,8000) # Timer Interrupt

    # Start Multithreading
    background = Background()                 # menjalankan init() Class Background 
    forward = Rectangle(fps)                  # menjalankan init() Class Rectangle 
    forward.start()
    background.start()

    # Start Multiprocessing
    timeout    = time.time()*1000.0
    TES = multiprocessing.process.Process(target=Main,args=(data,Ref,t1,t2,timeout))
    TES.daemon = True
    TES.start()

    while True :
        eventLoop()                       # Loop Utama
        clock.tick(60)                    # limit frame menjadi 60 fps

if __name__ == "__main__":
    #TES = process(processes=4)
    run()
