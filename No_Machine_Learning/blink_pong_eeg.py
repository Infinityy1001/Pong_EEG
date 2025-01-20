# *******************  IMPORTING MODULES ********************
from tkinter import *
import tkinter as tk
import time
import random
import threading
import pylsl
import subprocess

# *********************  G L O B A L S *********************
global isFailed

blinks = 0  
blinked = False 
jaw_clenches = 0 
jaw_clenched = False  


# Variables pour le stream EEG
eeg_stream = None
eeg_inlet = None


# ********** Initialisation du stream EEG **********
def init_eeg_stream():
    global eeg_stream, eeg_inlet

    # Lancer le stream EEG avec muselsl
    subprocess.Popen(['muselsl', 'stream'])

    # Attendre que le stream soit actif
    print("Recherche du stream EEG...")
    time.sleep(7.5)

    # Trouver le stream EEG
    print("Recherche des streams LSL...")
    streams = pylsl.resolve_byprop('type', 'EEG')
    if not streams:
        print("Aucun stream EEG trouvé.")
        return

    # Se connecter au stream EEG
    eeg_inlet = pylsl.StreamInlet(streams[0])
    print("Connecté au stream EEG.")

# ********** Lire les données EEG **********
def read_eeg_data():
    global blinked, jaw_clenched

    if eeg_inlet is None:
        return

    try:
        while True:
            # Obtenir un échantillon de données EEG
            sample, timestamp = eeg_inlet.pull_sample()

            # Exemple de détection de clignement (à adapter selon vos besoins)
            if sample[0] > 100:  # Seuil arbitraire pour détecter un clignement
                blinked = True
                print("Clignement détecté via EEG")

            # Exemple de détection de serrement de mâchoire (à adapter)
            if sample[1] > 100:  # Seuil arbitraire pour détecter un serrement
                jaw_clenched = True
                print("Serrement de mâchoire détecté via EEG")

    except Exception as e:
        print(f"Erreur lors de la lecture des données EEG : {e}")


# ********** Démarrer le thread EEG **********
def start_eeg_thread():
    init_eeg_stream()
    if eeg_inlet is not None:
        eeg_thread = threading.Thread(target=read_eeg_data)
        eeg_thread.daemon = True
        eeg_thread.start()

# ========================== G A M E  ==============================

# *********** Moving the paddle ***********
def movepaddleLR(paddle, dir, x, y=0):
    x1, y1, x2, y2 = c.coords(paddle)
    if ((x1 > 0 and dir == 'l') or (x2 < 400 and dir == 'r')):
        c.move(paddle, x, y)
        c.update()
    elif dir == 'stop':
        c.move(paddle, 0, 0)
        c.update()

# *********** Moving the ball ***********
def move_ball(ball, sp, score):
    global wait, blink_window_wait, blinked, jaw_window_wait, jaw_clenched

    s = random.randint(-sp, sp)
    x, y = s, 0 - sp
    c.move(ball, x, y)

    for p in range(1, 500000):
        l, t, r, b = c.coords(ball)
        txtS.delete(0, END)
        txtS.insert(0, "Score: " + str(score))

        if (r >= 400 and x >= 0 and y < 0):
            x, y = 0 - sp, 0 - sp
        elif (r >= 400 and x >= 0 and y >= 0):
            x, y = 0 - sp, sp
        elif (l <= 0 and x < 0 and y < 0):
            x, y = sp, 0 - sp
        elif (l <= 0 and x < 0 and y >= 0):
            x, y = sp, sp
        elif (t <= 0 and x >= 0 and y < 0):
            x, y = sp, sp
        elif (t <= 0 and x < 0 and y < 0):
            x, y = 0 - sp, sp
        elif (b >= 385):
            tchPt = l + 10
            bsl, bst, bsr, bsb = c.coords(paddle)
            if (tchPt >= bsl and tchPt <= bsr):
                n = random.randint(-sp, sp)
                x, y = n, 0 - sp
                score += 1
            else:
                wait += 1
                if wait == 5:
                    wait = 0
                    global isFailed
                    isFailed = True
                    break

        time.sleep(.025)

        if blinked == True:
            c.itemconfigure(blink_window, state='normal')
            blinked = False

        if blink_window_wait == 50:
            blink_window_wait = 0
            c.itemconfigure(blink_window, state='hidden')
        else:
            blink_window_wait += 1

        if jaw_clenched == True:
            c.itemconfigure(jaw_window, state='normal')
            jaw_clenched = False

        if jaw_window_wait == 50:
            jaw_window_wait = 0
            c.itemconfigure(jaw_window, state='hidden')
        else:
            jaw_window_wait += 1

        what = blinks % 4
        if what == 1:
            movepaddleLR(paddle, 'l', 0 - paddle_speed)
        elif what == 0 or what == 2:
            movepaddleLR(paddle, 'stop', 0)
        elif what == 3:
            movepaddleLR(paddle, 'r', paddle_speed)

        c.move(ball, x, y)
        c.update()

# ***** RESTARTING AFTER HITTING THE BOTTOM *****
def restart():
    global isFailed
    if (isFailed == True):
        isFailed = False
        c.moveto(paddle, 150, 385)
        c.moveto(ball, 190, 365)
        move_ball(ball, ball_speed, score)

# *************** INITIALISING ***************
def pong():
    global c, ball, txtS, paddle, blink_window, jaw_window, ball_speed, paddle_speed
    global score, wait, blink_window_wait, jaw_window_wait

    # Initialisation
    root = Tk()
    root.minsize(400, 400)
    root.title("Blink Pong")
    paddle_speed = 5
    ball_speed = 5
    score = 10
    wait = 0
    blink_window_wait = 0
    jaw_window_wait = 0
    global isFailed
    isFailed = False

    # Démarrer le thread EEG
    start_eeg_thread()

    # Canvas
    c = Canvas(width=400, height=400, background='#000000')
    c.pack()
    paddle = c.create_rectangle(150, 385, 250, 400, fill='white', outline='white')
    ball = c.create_oval(190, 365, 210, 385, fill='blue', outline='blue')
    txtS = tk.Entry(c, text='0',font=('Arial', 10, 'bold'), fg='white', bg='black')
    txtScore = c.create_window(300, 0, anchor='nw', window=txtS)

    # Fenêtres de détection
    blink_label = tk.Label(c, text='Blink detected!', fg='white', bg='black', font=('Arial', 10, 'bold'))
    blink_window = c.create_window(10, 10, anchor='nw', window=blink_label)
    c.itemconfigure(blink_window, state='hidden')

    jaw_label = tk.Label(c, text='Jaw clench detected!', fg='white', bg='black', font=('Arial', 10, 'bold'))
    jaw_window = c.create_window(140, 10, anchor='nw', window=jaw_label)
    c.itemconfigure(jaw_window, state='hidden')

    # Bind keys
    root.bind("<KeyPress-Left>", lambda event: movepaddleLR(paddle, 'l', 0 - paddle_speed))
    root.bind("<KeyPress-Right>", lambda event: movepaddleLR(paddle, 'r', paddle_speed))

    # Main loop
    while 1:
        move_ball(ball, ball_speed, score)
        score -= 1
    root.mainloop()

if __name__ == "__main__":
    pong()