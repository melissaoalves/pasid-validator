import threading
import socket
import time
import random
from domain.abstract_proxy import AbstractProxy

class ServiceProxy(AbstractProxy):
    def __init__(self, name, local_port, destiny_ip, destiny_port, service_time=100.0, service_std=2.0, target_is_source=False):
        super().__init__(name, local_port, destiny_ip, destiny_port)
        self.service_time = service_time
        self.service_std = service_std
        self.target_is_source = target_is_source
        self.interrupt = False

    def run(self):
        threading.Thread(target=self._connection_establishment_origin_thread, daemon=True).start()
        threading.Thread(target=self._connection_establishment_destiny_thread, daemon=True).start()
        print(f"Starting {self.proxy_name} on port {self.local_port}")

        while not self.interrupt:
            if self.has_something_to_process():
                self.process_and_send()
            else:
                time.sleep(0.1)

    def process_and_send(self):
        with self.lock:
            content = self.content_to_process
            self.content_to_process = None


        process_time = random.gauss(self.service_time, self.service_std)
        if process_time < 0:
            process_time = self.service_time
        time.sleep(process_time / 1000)

        if self.target_is_source:
            from domain.utils.utils import register_time
            content = register_time(content)

        try:
            self.send_message_to_destiny(content + "\n")
            print(f"{self.proxy_name} sent processed message.")
        except Exception as e:
            print(f"{self.proxy_name} error sending message: {e}")

    def receiving_messages(self, client_socket):
        print(f"{self.proxy_name} enabled to receive messages.")
        with client_socket:
            while True:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    msg = data.decode().strip()
                    if msg == "ping":
                        client_socket.sendall(b"free\n")
                    else:
                        self.set_content_to_process(msg)
                except Exception as e:
                    print(f"{self.proxy_name} error receiving message: {e}")
                    break

    def stop_service(self):
        self.interrupt = True
        self.stop()
