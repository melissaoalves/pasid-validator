import threading
import socket
from abc import ABC
import time

class AbstractProxy(threading.Thread, ABC):
    def __init__(self, proxy_name: str, local_port: int, destiny_ip='localhost', destiny_port=None):
        super().__init__()
        self.proxy_name = proxy_name
        self.local_port = local_port
        self.destiny_ip = destiny_ip
        self.destiny_port = destiny_port
        self.local_socket = None
        self.connection_destiny_socket = None
        self.content_to_process = None
        self.lock = threading.Lock()
        self.running = True

    def run(self):
        threading.Thread(target=self._connection_establishment_origin_thread, daemon=True).start()
        threading.Thread(target=self._connection_establishment_destiny_thread, daemon=True).start()
        print(f"{self.proxy_name} started and listening on port {self.local_port}")

        while self.running:
            if self.has_something_to_process():
                with self.lock:
                    print(f"{self.proxy_name} processing: {self.content_to_process}")
                    self.content_to_process = None
            time.sleep(0.1)

    def _connection_establishment_origin_thread(self):
        self.local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.local_socket.bind(('localhost', self.local_port))
        self.local_socket.listen()
        print(f"{self.proxy_name}: Waiting for incoming connections...")

        while self.running:
            try:
                client_socket, addr = self.local_socket.accept()
                threading.Thread(target=self.receiving_messages, args=(client_socket,), daemon=True).start()
            except Exception as e:
                print(f"{self.proxy_name}: Error accepting connection: {e}")

    def _connection_establishment_destiny_thread(self):
        connected = False
        while not connected and self.running:
            try:
                self.create_connection_with_destiny()
                connected = True
                print(f"{self.proxy_name}: Connected to destiny at {self.destiny_ip}:{self.destiny_port}")
            except Exception:
                print(f"{self.proxy_name}: Connection failed, retrying in 1s...")
                time.sleep(1)

    def create_connection_with_destiny(self):
        if self.destiny_port is None:
            raise ValueError("Destiny port not set.")
        self.connection_destiny_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection_destiny_socket.connect((self.destiny_ip, self.destiny_port))

    def receiving_messages(self, client_socket: socket.socket):
        print(f"{self.proxy_name}: Started receiving messages")
        with client_socket:
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    message = data.decode()
                    print(f"{self.proxy_name} received: {message.strip()}")
                    self.set_content_to_process(message.strip())
                except Exception as e:
                    print(f"{self.proxy_name}: Error receiving message: {e}")
                    break

    def has_something_to_process(self):
        with self.lock:
            return self.content_to_process is not None

    def set_content_to_process(self, content: str):
        with self.lock:
            self.content_to_process = content

    def send_message_to_destiny(self, message: str):
        if not self.connection_destiny_socket:
            raise ConnectionError("No connection to destiny socket.")
        try:
            self.connection_destiny_socket.sendall(message.encode())
        except Exception as e:
            print(f"{self.proxy_name}: Error sending message: {e}")

    def is_destiny_free(self):
        try:
            self.connection_destiny_socket.sendall(b"ping\n")
            self.connection_destiny_socket.settimeout(2.0)
            response = self.connection_destiny_socket.recv(1024).decode().strip()
            return response == "free"
        except Exception:
            return False

    def stop(self):
        self.running = False
        if self.local_socket:
            self.local_socket.close()
        if self.connection_destiny_socket:
            self.connection_destiny_socket.close()
        print(f"{self.proxy_name} stopped.")
