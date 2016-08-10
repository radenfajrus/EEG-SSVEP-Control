from pygame.locals import *
import pygame, os

 #
 # Editable Configuration
 #

fps             = 60
frequency       = {
    'forward'   : 9,
    'stop'      : 10,
    'right'     : 11,
    'left'      : 12
}

images_folder   = 'images'
filename        = {
    'stop'          : 'circle-stop.png',
    'left'          : 'arrow-left.png',
    'right'         : 'arrow-right.png',
    'forward'       : 'arrow-forward.png',
    'fill_left'     : 'fill-left.png',
    'fill_right'    : 'fill-right.png',
    'fill_forward'  : 'fill-forward.png',
}

side_divider    = 4
grid            = 4         # column and row
position        = {         # based on grid
    'stop'      : (2, 3),
    'left'      : (1, 3),
    'right'     : (3, 3),
    'middle'    : (2, 2),
    'forward'   : (2, 1)
}

 #
 # Environment Class
 # @param int screenWidth
 # @param int screenHeight
 #

class Env():
    def __init__(self, screenWidth, screenHeight, name='Stimulus Environment') :
        self.__clr_white    = (255, 255, 255)
        self.__clr_black    = (0, 0, 0)
        self.__clr_red      = (255, 0, 0)
        self.__clr_green    = (0, 255, 0)
        self.__clr_blue     = (0, 0, 255)
        self.__clr_yellow   = (234, 235, 189)

        self.__width        = screenWidth
        self.__height       = screenHeight
        self.__resolution   = (self.__width, self.__height)

        self.__side         = self.__height / side_divider

        self.__run          = True
        self.__stop         = False

        self.__fps          = fps
        self.__frq_forward  = frequency['forward']
        self.__frq_stop     = frequency['stop']
        self.__frq_right    = frequency['right']
        self.__frq_left     = frequency['left']

        self.__img_stop     = self.__setImage('stop')
        self.__img_left     = self.__setImage('left')
        self.__img_right    = self.__setImage('right')
        self.__img_forward  = self.__setImage('forward')
        self.__fill_left    = self.__setImage('fill_left')
        self.__fill_right   = self.__setImage('fill_right')
        self.__fill_forward = self.__setImage('fill_forward')

        self.__pos_stop     = self.__setRectPosition(grid, position['stop'])
        self.__pos_left     = self.__setRectPosition(grid, position['left'])
        self.__pos_right    = self.__setRectPosition(grid, position['right'])
        self.__pos_middle   = self.__setRectPosition(grid, position['middle'])
        self.__pos_forward  = self.__setRectPosition(grid, position['forward'])

    def killStop(self)      : self.__stop = True
    def changeRun(self)     : self.__run  = not self.__run

    def getFPS(self)        : return self.__fps
    def getRun(self)        : return self.__run
    def getStop(self)       : return self.__stop
    def getResolution(self) : return self.__resolution
    def getRectSize(self)   : return (self.__side, self.__side)

    def getColor(self, state=None)      :
        return {
            'white'         : self.__clr_white,
            'black'         : self.__clr_black,
            'red'           : self.__clr_red,
            'green'         : self.__clr_green,
            'blue'          : self.__clr_blue,
            'yellow'        : self.__clr_yellow
        }.get(state, self.__clr_white)

    def getRectIMG(self, state=None)    :
        return {
            'stop'          : self.__img_stop,
            'left'          : self.__img_left,
            'right'         : self.__img_right,
            'forward'       : self.__img_forward,
            'fill_left'     : self.__fill_left,
            'fill_right'    : self.__fill_right,
            'fill_forward'  : self.__fill_forward
        }.get(state, self.__img_stop)

    def getRectFreq(self, state=None)    :
        return {
            'stop'          :self.__frq_stop,
            'left'          :self.__frq_left,
            'right'         :self.__frq_right,
            'forward'       :self.__frq_forward
        }.get(state, self.__frq_stop)

    def getRectPos(self, state=None)    :
        return {
            'stop'          : self.__pos_stop,
            'left'          : self.__pos_left,
            'right'         : self.__pos_right,
            'middle'        : self.__pos_middle,
            'forward'       : self.__pos_forward,
        }.get(state, self.__pos_middle)

    def __setImage(self, state) :
        fullpath            = os.path.join(images_folder, filename[state])
        raw_img             = pygame.image.load(fullpath)

        return pygame.transform.scale(raw_img, (self.__side, self.__side))

    def __setRectPosition(self, grid, pos) :
        X   = (self.__width / grid) * pos[0] - (self.__side / 2)
        Y   = (self.__height / grid) * pos[1] - (self.__side / 2)

        return (X, Y)
