import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'event type: {event.event_type} path : {event.src_path}')
    def on_created(self, event):
        print(f'event type: {event.event_type} path : {event.src_path}')
    def on_deleted(self, event):
        print(f'event type: {event.event_type} path : {event.src_path}')
    def on_moved(self, event):
        print(f'event type: {event.event_type} from {event.src_path} to {event.dest_path}')

if __name__ == "__main__":
    path = "C:\\Your\\Directory\\To\\Monitor"  # Replace with the path you want to monitor
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()import psutil
import time

def monitor_network():
    while True:
        connections = psutil.net_connections()
        for conn in connections:
            print(f"Local Address: {conn.laddr}, Remote Address: {conn.raddr}, Status: {conn.status}")
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__"
    monitor_network()
pip-installer.enable
resourceWatchdog.battery.show
resourceWatchdog.cpuFrequency.show
resourceWatchdog.cpuFrequency.unitGHz

resourceWatchdog.memory.dangerThreshold