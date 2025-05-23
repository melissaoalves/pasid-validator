import yaml
import threading
import random
import time
from domain.abstract_proxy import AbstractProxy
from domain.target_address import TargetAddress
from domain.service_proxy import ServiceProxy

class LoadBalancerProxy(AbstractProxy):
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        server_cfg = config.get("server", {})
        service_cfg = config.get("service", {})

        proxy_name = server_cfg.get("loadBalancerName", "LoadBalancer")
        local_port = server_cfg.get("loadBalancerPort", 2000)
        self.queue_max_size = server_cfg.get("queueLoadBalancerMaxSize", 100)
        self.qtd_services_list = server_cfg.get("qtdServices", [1])

        self.service_target_ip = service_cfg.get("targetIp", "localhost")
        self.service_target_port = service_cfg.get("targetPort", 3000)
        self.service_time = service_cfg.get("serviceTime", 100.0)
        self.service_std = service_cfg.get("std", 2.0)
        self.target_is_source = service_cfg.get("targetIsSource", False)

        super().__init__(proxy_name, local_port, self.service_target_ip, self.service_target_port)

        self.queue = []
        self.queue_lock = threading.Lock()

        self.services = []
        self.service_addresses = []

        self._create_services()

        self.current_service_index = 0

    def _create_services(self):
        num_services = self.qtd_services_list[0] if self.qtd_services_list else 1
        base_port = self.local_port + 1
        for i in range(num_services):
            port = base_port + i
            ta = TargetAddress("localhost", port)
            sp = ServiceProxy(
                name=f"service{port}",
                local_port=port,
                destiny_ip=self.service_target_ip,
                destiny_port=self.service_target_port,
                service_time=self.service_time,
                service_std=self.service_std,
                target_is_source=self.target_is_source,
            )
            sp.start()
            self.services.append(sp)
            self.service_addresses.append(ta)

    def has_something_to_process(self):
        with self.queue_lock:
            return len(self.queue) > 0

    def add_message_to_queue(self, msg):
        with self.queue_lock:
            if len(self.queue) < self.queue_max_size:
                self.queue.append(msg)
                return True
            else:
                return False

    def run(self):
        threading.Thread(target=self._connection_establishment_origin_thread, daemon=True).start()
        threading.Thread(target=self._connection_establishment_destiny_thread, daemon=True).start()
        print(f"{self.proxy_name} started on port {self.local_port}")

        while True:
            if self.has_something_to_process():
                msg = None
                with self.queue_lock:
                    if self.queue:
                        msg = self.queue.pop(0)

                if msg:
                    sent = False
                    while not sent:
                        service = self.services[self.current_service_index]
                        if service.is_destiny_free():
                            try:
                                service.send_message_to_destiny(msg)
                                sent = True
                                print(f"{self.proxy_name} sent message to {service.proxy_name}")
                            except Exception as e:
                                print(f"{self.proxy_name} error sending message: {e}")
                        else:
                            print(f"{self.proxy_name} waiting for service {service.proxy_name} to be free")

                        # Round robin
                        self.current_service_index = (self.current_service_index + 1) % len(self.services)
                        time.sleep(0.1)
            else:
                time.sleep(0.1)

    def receiving_messages(self, client_socket):
        print(f"{self.proxy_name} enabled to receive messages.")
        with client_socket:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                msg = data.decode()
                if msg.strip() == "ping":
                    client_socket.sendall(b"free\n")
                else:
                    added = self.add_message_to_queue(msg.strip())
                    if not added:
                        print(f"{self.proxy_name} queue full. Dropping message.")

