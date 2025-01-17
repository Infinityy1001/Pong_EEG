import subprocess
import time

stream_process = subprocess.Popen(['muselsl', 'stream'])

time.sleep(15)

input("Appuyez sur Entrée pour arrêter le stream ...")

stream_process.terminate()

stream_process.wait()

print("Stream arrêtés.")