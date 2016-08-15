from emotiv import Emotiv
from datetime import datetime
from preprocess import *
import multiprocessing

import os, sys, time, errno, platform
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

if __name__ == "__main__":
    # headset = Emotiv(display_output=False)
    Q = multiprocessing.Queue()
    headset     = Emotiv()
    gevent.spawn(headset.setup)
    gevent.sleep(0)

    folder      = 'data/' + datetime.now().strftime('%Y%m%d') + '/'
    filename    = datetime.now().strftime('%H%M%S') + "_" + name + "_" + str(maxtime) + ".csv"

    fullpath    = os.path.join(folder, filename)

    if not os.path.exists(os.path.dirname(fullpath)):
        try:
            os.makedirs(os.path.dirname(fullpath))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    output      = open(fullpath, 'w')

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
    fs = 4
    data,data2 = range(fs),range(fs)
    i = 0
    second      = 0
    first       = -1
    try:
        start_time      = int(round(time.time() * 1000))
        #print "2"
        while ( second < maxtime ):
            #print "3"
            time_now    = int(round(time.time() * 1000)) - start_time 
            packet      = headset.dequeue()
            Q.put(packet.counter)

            # output.write("%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (time.time(), packet.counter, packet.F3[0], packet.FC5[0], packet.AF3[0], packet.F7[0], packet.T7[0], packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.T8[0], packet.F8[0], packet.AF4[0], packet.FC6[0], packet.F4[0], packet.gyro_x, packet.gyro_y))
            # output.write("%i,%s,%s,%s,%s,%s,%s,%s\n" % (time_now, packet.counter, packet.P7[0], packet.O1[0], packet.O2[0], packet.P8[0], packet.gyro_x, packet.gyro_y))
            #Q.put(packet.battery)
            if not packet.counter == 128 :
                data[i] = packet.battery,packet.counter
                i = (i + 1) % fs
                j = (i + 1) % fs
                k = 0
                while j != i :
                    #print "@"
                    data2[k] = data[j-1]
                    j = (j + 1)%fs
                    k = k + 1
                data2[k] = data[(j-1)%fs]
            if packet.counter == 128:
                print Q.empty()
                second = second + 1
                start_time      = int(round(time.time() * 1000))
            gevent.sleep(0)

    except KeyboardInterrupt:
        headset.close()
        #os.system('cls')
    finally:
        headset.close()
        #os.system('cls')
