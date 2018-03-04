import csv
import serial
import time
import controller

portname = 'COM8'

def main():
    with open('monitor.log', 'w+') as log:
        log.write('Initialization\n')
        with serial.Serial(portname, timeout=1) as port:
            log.write('Port opened on port ' + portname + '\n')
            controller.init_plate(port, log) #Send initialization commands
            with open('monitor_plot.csv', 'w+', newline='') as plotfile:
                plotwriter = csv.writer(plotfile, delimiter='\t', dialect='excel')
                start_time = time.time()
                while(True):
                    try:
                        controller.monitor(port, plotwriter, start_time)
                        time.sleep(0.5)
                    except:
                        print('', flush=True)
                        break

if __name__ == "__main__":
    main()
