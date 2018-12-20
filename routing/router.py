import json
from json import JSONDecodeError
from random import choice
from threading import Timer
import math

from routing.router_port import RouterPort


class Router(object):
    def __init__(self, name, update_time, ports, logging=True):
        self.name = name
        self.update_time = update_time
        self.ports = dict()
        self.route_table = dict()     # Route table {R#N : port out}
        self.name_port = dict()       # Name port {R#N : port in}
        self.distance_vector = dict() # Distance vector {port in : distance}
        self._init_ports(ports)
        self.timer = None
        self.logging = logging

    def _success(self, message):
        """
        Internal method called when a packet is successfully received.
        :param message:
        :return:
        """
        print("[{}] {}: {}".format(self.name, 'Success! Data', message))

    def _log(self, message):
        """
        Internal method to log messages.
        :param message:
        :return: None
        """
        if self.logging:
            print("[{}] {}".format(self.name, message))

    def _init_ports(self, ports):
        """
        Internal method to initialize the ports.
        :param ports:
        :return: None
        """
        for port in ports:
            input_port = port['input']
            output_port = port['output']

            router_port = RouterPort(
                input_port, output_port, lambda p: self._new_packet_received(p)
            )

            self.ports[output_port] = router_port
            self.interface[output_port] = input_port  # Par puerto in - puerto out
        self.distance_vector[self.name] = 0           # Agrega el par {self.name, 0}

        for p in self.ports:
            send_packet(p, json.dumps({'destination': "Broadcast",
                                              'data': {"name": self.name,
                                                       "port": self.interface[p],
                                                     "Hello" : 1,
                                                       "msg" : "Hello request",
                                                   "d_vector": self.distance_vector,
                                                    "r_table": self.route_table},
                                               'hop': 1
                                               }))

    def _new_packet_received(self, packet):
        """
        Internal method called as callback when a packet is received.
        :param packet:
        :return: None
        """
        self._log("Packet received")
        message = packet.decode()

        try:
            message = json.loads(message)
        except JSONDecodeError:
            self._log("Malformed packet")
            return

        if 'destination' in message and 'data' in message:
            if message['destination'] == self.name or message['destination'] == "Broadcast":
                self._success(message['data']['msg'])
                # Hello == 1 es el inicio de intercambio de vectores de distancia
                if message['data']["Hello"]:
                    r_table = message['data']['r_table']
                    d_vector = message['data']['d_vector']
                    name = message["data"]["name"] # R#N of the sender
                    port = message["data"]["port"] # Output port for the router receiving
                    hop = message["hop"]
                    # Recorremos los nombres del vector de distancia recibidos
                    for n in d_vector:
                        # Si un nombre no se encuentra en nuestro vector de distancia o si es menor el camino
                        if not(n in self.distance_vector) or (d_vector[n] + hop < self.distance_vector[n]):
                            self.distance_vector[n] = d_vector[n] + hop     # Agregamos el nombre y su distancia + n° de hop de mensaje
                            self.route_table[n] = port                      # Agrega el nombre del router no agregado y el puerto del enviador como salida
            else:
                # If a port already exists for destination
                if message['destination'] in self.route_table:
                    port = self.route_table[message['destination']]

                else:
                    # Randomly choose a port to forward
                    port = choice(list(self.ports.keys()))
                self._log("Forwarding to port {}".format(port))
                self.ports[port].send_packet(packet)
        else:
            self._log("Malformed packet")

    def _broadcast(self):
        """
        Internal method to broadcast
        :return: None
        """
        self._log("Broadcasting")
        for p in self.ports:
            send_packet(p, json.dumps({'destination': "Broadcast",
                                              'data': {"name": self.name, "Hello" : 0,
                                                       "port": self.port, "ACK": 0,
                                                        "msg": "Connection request",
                                                "route_table": self.route_table},
                                              }))
        self.timer = Timer(self.update_time, lambda: self._broadcast())
        self.timer.start()

    def start(self):
        """
        Method to start the routing.
        :return: None
        """
        self._log("Starting")
        self._broadcast()
        for port in self.ports.values():
            port.start()

    def stop(self):
        """
        Method to stop the routing.
        Is in charge of stop the router ports threads.
        :return: None
        """
        self._log("Stopping")
        if self.timer:
            self.timer.cancel()

        for port in self.ports.values():
            port.stop_running()

        for port in self.ports.values():
            port.join()

        self._log("Stopped")
