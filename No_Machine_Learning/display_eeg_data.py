import subprocess
import time
from pylsl import StreamInlet, resolve_byprop  

# Lancer le stream EEG avec muselsl
stream_process = subprocess.Popen(['muselsl', 'stream'])

# Attendre que le stream soit actif
print("Recherche du stream EEG...")
time.sleep(7.5) 

# Trouver le stream EEG
print("Recherche des streams LSL...")
streams = resolve_byprop('type', 'EEG')
if not streams:
    print("Aucun stream EEG trouvé.")
    stream_process.terminate()
    stream_process.wait()
    exit()

# Se connecter au stream EEG
inlet = StreamInlet(streams[0])
print("Connecté au stream EEG.")

# Lire et afficher les données en temps réel
try:
    while True:
        # Obtenir un échantillon de données
        sample, timestamp = inlet.pull_sample()
        time.sleep(1)
        print(f"Timestamp: {timestamp}, Données EEG: {sample}")

except KeyboardInterrupt:
    print("Arrêt de la lecture des données.")

# Arrêter le stream
stream_process.terminate()
stream_process.wait()
print("Stream arrêté.")