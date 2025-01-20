#################################################################
#                       B L I N K   P O N G                     #
#################################################################

# Very simple Pong game, assembled from bits and pieces by Thomas Vikström
# The objective is to try to increase the score by hitting the ball
# Uses Muse EEG-device and LSL for streaming EEG data

# *******************  IMPORTING MODULES ********************

from tkinter import *
import tkinter as tk
import time
import random
import threading
import numpy as np
import tensorflow as tf
from nltk import flatten
import pylsl
import subprocess

# *********************  G L O B A L S *********************

alpha = beta = delta = theta = gamma = [-1, -1, -1, -1]
all_waves = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
all_samples = []

sample_nr = 0
expected_samples = 20  # there are 5 frequencies (alpha...gamma) and 4 sensors, if all 4 sensors are used
                       # this should be 5 x 4 = 20, the frequency is 10 Hz. 2 seconds of data with all
                       # 4 sensors = 2 * 5 * 4 * 10 = 400.

confidence_threshold = 0.6  # default in Edge Impulse is 0.6
global isFailed
blinks = 0  # amount of blinks
blinked = False  # did you blink?

# Variables pour le stream EEG
eeg_stream = None
eeg_inlet = None

# ==========================================================
# *******************  F U N C T I O N S *******************
# ==========================================================

# *********** Fonction pour ajuster la taille des données ***********
def pad_data(input_samples, target_size=600):
    # Si les données sont déjà de la bonne taille, on ne fait rien
    if len(input_samples) >= target_size:
        return input_samples[:target_size]
    
    # Sinon, on ajoute des zéros pour atteindre la taille cible
    padded_data = np.zeros(target_size)
    padded_data[:len(input_samples)] = input_samples
    return padded_data

# *********** Initiates TensorFlow Lite ***********
def initiate_tf():
    global interpreter, input_details, output_details

    ####################### INITIALIZE TF Lite #########################
    # Load TFLite model and allocate tensors.
    interpreter = tf.lite.Interpreter(r"Models\model.lite")  # Utilisation de raw string pour éviter l'erreur d'échappement

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Allocate tensors
    interpreter.allocate_tensors()

    # Printing input and output details for debug purposes in case anything is not working
    print(input_details)
    print(output_details)

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
    global blinked, all_samples, sample_nr, expected_samples

    if eeg_inlet is None:
        return

    try:
        while True:
            # Obtenir un échantillon de données EEG
            sample, timestamp = eeg_inlet.pull_sample()

            # Ajouter les données à all_waves
            for i in range(len(sample)):
                all_waves[i] = sample[i]

            all_samples.append(all_waves.copy())  # Appending all data...
            sample_nr += 1

            if sample_nr == expected_samples:  # Collected all samples...
                all_samples_flat = flatten(all_samples)  # ...and flattening them
                inference(all_samples_flat)  # Inference function call
                sample_nr = 0
                all_samples.clear()
                all_samples = []

    except Exception as e:
        print(f"Erreur lors de la lecture des données EEG : {e}")

# ******** INFERENCE ********
def inference(input_samples):
    global score, expected, choice, blinks, blinked

    # Ajuster la taille des données à 600 éléments
    input_samples = pad_data(input_samples, target_size=600)

    input_samples = np.array(input_samples, dtype=np.float32)
    input_samples = np.expand_dims(input_samples, axis=0)

    # input_details[0]['index'] = the index which accepts the input
    interpreter.set_tensor(input_details[0]['index'], input_samples)

    # run the inference
    interpreter.invoke()

    # output_details[0]['index'] = the index which provides the input
    output_data = interpreter.get_tensor(output_details[0]['index'])

    # finding output data
    blink = output_data[0][0]
    background = output_data[0][1]

    # checking if over confidence threshold
    if blink >= confidence_threshold:
        choice = "Blink"
        blinks += 1
        blinked = True
    elif background >= confidence_threshold:
        choice = "Background"
    else:
        choice = "----"

    print(f"Blink:{blink:.4f} - Background:{background:.4f}     {choice}          ")

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
    if ((x1 > 0 and dir == 'l') or (x2 < 400 and dir == 'r')):  # if within bounds, moving left or right
        c.move(paddle, x, y)
        c.update()
    elif dir == 'stop':  # if asked to stop moving
        c.move(paddle, 0, 0)
        c.update()

# *********** Moving the ball ***********
def move_ball(ball, sp, score):
    global wait, blink_window_wait, blinked

    s = random.randint(-sp, sp)
    x, y = s, 0 - sp
    c.move(ball, x, y)

    for p in range(1, 500000):  # "Infinite" loop
        l, t, r, b = c.coords(ball)  # fetching coordinates
        txtS.delete(0, END)  # emptying the score window...
        txtS.insert(0, "Score: " + str(score))  # ...and refilling it again with current score

        # Need to change direction when hitting the wall. There are eight options
        if (r >= 400 and x >= 0 and y < 0):  # Ball moving ↗ and hit right wall
            x, y = 0 - sp, 0 - sp
        elif (r >= 400 and x >= 0 and y >= 0):  # Ball moving ↘ and hit right wall
            x, y = 0 - sp, sp
        elif (l <= 0 and x < 0 and y < 0):  # Ball moving ↖ and hit left wall
            x, y = sp, 0 - sp
        elif (l <= 0 and x < 0 and y >= 0):  # Ball moving ↙ and hit left wall
            x, y = sp, sp
        elif (t <= 0 and x >= 0 and y < 0):  # Ball moving ↗ and hit top wall
            x, y = sp, sp
        elif (t <= 0 and x < 0 and y < 0):  # Ball moving ↖ and hit top wall
            x, y = 0 - sp, sp
        elif (b >= 385):  # Ball reached paddle level. Check if paddle touches ball
            tchPt = l + 10  # Size is 20. Half of it.
            bsl, bst, bsr, bsb = c.coords(paddle)
            if (tchPt >= bsl and tchPt <= bsr):  # Ball touches paddle
                n = random.randint(-sp, sp)
                x, y = n, 0 - sp
                score += 1
            else:  # Oh no, we hit the bottom!
                wait += 1  # Waiting to let the ball hit the bottom, more or less
                if wait == 5:
                    wait = 0
                    global isFailed
                    isFailed = True
                    break  # Breaking out of the function

        time.sleep(.050)  # Dare to remove this? Speed of the ball

        if blinked == True:  # Did you blink? Yes...
            c.itemconfigure(blink_window, state='normal')  # ...showing a message that you did...
            blinked = False

        if blink_window_wait == 50:  # ...for a short while...
            blink_window_wait = 0
            c.itemconfigure(blink_window, state='hidden')  # ...until we hide it
        else:
            blink_window_wait += 1

        what = blinks % 4  # % = modulo, we have 4 states, 2 of them pausing:
        if what == 1:  # -> STOP -> LEFT -> STOP -> RIGHT
            movepaddleLR(paddle, 'l', 0 - paddle_speed)  # moving left
        elif what == 0 or what == 2:
            movepaddleLR(paddle, 'stop', 0)  # stopping
        elif what == 3:
            movepaddleLR(paddle, 'r', paddle_speed)  # moving right

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
    global c, ball, txtS, paddle, blink_window, ball_speed, paddle_speed
    global score, wait, blink_window_wait

    # misc. initialisation stuff
    root = Tk()
    root.minsize(400, 400)
    root.title("Blink Pong")
    paddle_speed = 5
    ball_speed = 5
    score = 10
    wait = 0
    blink_window_wait = 0
    global isFailed
    isFailed = False

    # Démarrer le thread EEG
    start_eeg_thread()

    # canvas related stuff
    c = Canvas(width=400, height=400, background='#000000')
    c.pack()
    paddle = c.create_rectangle(150, 385, 250, 400, fill='white', outline='white')
    ball = c.create_oval(190, 365, 210, 385, fill='blue', outline='blue')
    txtS = tk.Entry(c, text='0', font=('Arial', 16), fg='white', bg='black', bd=0, justify='center')
    txtScore = c.create_window(780, 10, anchor='ne', window=txtS)

    # blink detection window related stuff
    blink_label = tk.Label(c, text='Blink detected!', fg='white', bg='black', font=('Arial', 12, 'bold'))
    blink_window = c.create_window(10, 10, anchor='nw', window=blink_label)
    c.itemconfigure(blink_window, state='hidden')

    # left and right keys can be used when the paddle is STOPPED (blink once if the keys are not working)
    root.bind("<KeyPress-Left>", lambda event: movepaddleLR(paddle, 'l', 0 - paddle_speed))
    root.bind("<KeyPress-Right>", lambda event: movepaddleLR(paddle, 'r', paddle_speed))

    # main "infinite" loop
    while 1:
        move_ball(ball, ball_speed, score)  # if the ball hit the bottom, we escaped out...
        score -= 1  # ...of the function and decrease the score
    root.mainloop()

if __name__ == "__main__":
    initiate_tf()
    pong()  # Start Ponging!