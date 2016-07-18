import pygame, sys, thread, time, os
import numpy as np
from pygame.locals import *

pygame.init()
info        = pygame.display.Info()
clock       = pygame.time.Clock()

width       = info.current_w
height      = info.current_h

display     = (width, height)
screen      = pygame.display.set_mode(display, pygame.FULLSCREEN)

try :
    fps     = int(sys.argv[1])
except:
    fps     = 10

clr_white   = (255, 255, 255)
clr_black   = (0, 0, 0)
clr_red     = (255, 0, 0)
clr_green   = (0, 255, 0)
clr_blue    = (0, 0, 255)

clr_back    = clr_black
clr_default = clr_white

def_side    = height / 4

screen.fill(clr_back)

img_loc     = os.path.join("images", "circle-stop.png")
title_loc   = os.path.join("images", "title.png")
img         = pygame.image.load(img_loc)
img         = pygame.transform.scale(img, (def_side, def_side))
title       = pygame.image.load(title_loc).convert()
title       = pygame.transform.scale(title, (def_side, def_side/3))

class Rectangle():
    def __init__(self, fps) :
        self.clock      = pygame.time.Clock()
        self.last_tick  = pygame.time.get_ticks()
        self.rect       = pygame.Surface((def_side, def_side))
        self.rect2      = pygame.Surface((def_side, def_side))
        self.up         = 0
        self.run        = True
        self.fps        = fps * 2
        self.j          = 0
        self.i          = 1
        self.value      = 0
        self.value2     = 0        
        self.valuea     = 90
        self.value2a    = 10
        self.screen2    = pygame.display.get_surface()

        #self.rect2.fill(clr_default)
        self.rect2.set_alpha(30)
        self.rect2.blit(title,(0,0))

        while True :
            self.loop()        
                       

    def loop(self) :
        self.eventLoop()
        self.clock.tick(self.fps)
        # self.last_tick = pygame.time.get_ticks()



        if (self.run) :
            if (self.up) :
                self.rect.fill(clr_default)
                self.rect.blit(img, (0, 0))

                self.up  = 0
            else :
                self.rect.fill(clr_back)

                self.up  = 1
            
            if self.value != self.valuea:
                self.value = (self.value + (self.valuea - self.value)/5.0)
            if self.value2 != self.value2a:
                self.value2 = (self.value2 + (self.value2a - self.value2)/5.0)

            #print self.value,self.valuea,self.value2,self.value2a

            self.j = round((np.sin(2*np.pi*self.i*1/120)+1.5)*100)
            self.k1 = (np.sin(2*np.pi*self.i*1/30 + np.pi/2)+1)*np.sin(np.pi*self.value/100)*10
            self.k2 = (np.sin(2*np.pi*self.i*1/30)+1)*np.sin(np.pi*self.value2/100)*10
            self.i = (self.i + 1)%120   
            
            if self.i == 119:
                self.value2a = round(self.value)
                self.valuea = round(self.value2)

            self.screen2.fill(clr_back)  
            pygame.draw.rect(self.screen2, (0,105,0), pygame.Rect(width-(def_side*1.3),def_side+(self.k1)+(2*def_side*(100-self.value)/100),def_side/10,def_side*2-(self.k1)-(2*def_side*(100-self.value)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))
            pygame.draw.rect(self.screen2, (0,0,130), pygame.Rect((width-def_side),def_side+(self.k2)+(2*def_side*(100-self.value2)/100),def_side/10,def_side*2-(self.k2)-(2*def_side*(100-self.value2)/100)))#def_side,(def_side), (def_side)+10,(def_side)+50))

            pygame.draw.rect(self.screen2, (0,125-(self.j/2),0), pygame.Rect(width-(def_side*1.3),def_side,def_side/10,def_side*2), 3)
            pygame.draw.rect(self.screen2, (0,0,125-(self.j/2)), pygame.Rect((width-def_side),def_side,def_side/10,def_side*2), 3)

            #self.rect2.set_alpha(self.j)
            myfont = pygame.font.SysFont("monospace", 25)

            # render text
            label = myfont.render(str(int(round(self.value)))+"%", 3, (0,155,0))
            screen.blit(label, (width-(def_side*1.35),def_side*3.05))
            label2 = myfont.render(str(int(round(self.value2)))+"%", 3, (0,0,155))
            screen.blit(label2, ((width-(def_side*1.05)), def_side*3.05))

            labela = myfont.render("10 Hz", 3, (0,155,0))
            screen.blit(labela, (width-(def_side*1.4),def_side*3.18))
            labela2 = myfont.render("12 Hz", 3, (0,0,155))
            screen.blit(labela2, ((width-(def_side*1.08)), def_side*3.18))

            screen.blit(self.rect2, ((width/10, height/10)))    

        else :
            self.rect.fill(clr_default)
            self.rect.blit(img, (0, 0))

        # self.rect.set_alpha(self.alpha)

        screen.blit(self.rect, ((width - def_side) / 2 , (height - def_side) / 2 ))

        pygame.display.update(0,0,width,height)#(((width - def_side) / 2), ((height - def_side) / 2), def_side, def_side))

    def eventLoop(self) :
        for event in pygame.event.get():
            if event.type == QUIT :
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN :
                if event.key == K_ESCAPE :
                    pygame.quit()
                    sys.exit()
                if event.key == K_SPACE :
                    self.run = not self.run

def run() :
    forward = Rectangle(fps)

if __name__ == "__main__":
    run()
