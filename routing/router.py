import json
from json import JSONDecodeError
from random import choice
from threading import Timer
import math

from routing.router_port import RouterPort
MAX_HOP = 16

class Router(object):
    def __init__(self, name, update_time, ports, logging=True):
        self.name = name
        self.update_time = update_time
        self.ports = dict()
        self.route_table = dict()     # Table de ruta {R#N : puerto output}
        self.distance_vector = dict() # Vector de distancia {puerto input : distance}
        self.interface = dict()       # Pares {puerto output : puerto input}
        self._init_ports(ports)
        self.timer = None
        self.logging = logging
        self.default_port = 0         # Puerto default cuando no se encuentra en la tabla de ruta
        self.dvchanged = False        # Booleano para evaluar si el vector de distancia cambio
        # Iniciar pruebas
        # from topology import start, stop
        # from send_packet import send_packet
        # import json
        # routers = start('topology.json')
        # stop(routers)

        # Utilizar para las pruebas
        # send_packet(4321, json.dumps({'destination': 'Router#1','data': {'Hello' : 0,'msg' : 'Saludos a ti Router#1!'}, 'hop': 0}))
        # send_packet(4321, json.dumps({'destination': 'Router#2','data': {'Hello' : 0,'msg' : 'Saludos a ti Router#2!'}, 'hop': 0}))
        # send_packet(4321, json.dumps({'destination': 'Router#3','data': {'Hello' : 0,'msg' : 'Saludos a ti Router#3!'}, 'hop': 0}))
        # send_packet(4321, json.dumps({'destination': 'Router#4','data': {'Hello' : 0,'msg' : 'Saludos a ti Router#4! (inexistente)'}, 'hop': 0}))


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

            self.ports[output_port] = router_port     # Asignacion de objeto Router a puerto output
            self.interface[output_port] = input_port  # Par puerto in - puerto out de la interface
        self.distance_vector[self.name] = 0           # La distancia al Router propio es 0
        # Envio de mensajes Hello request (para conocer los routers proximos)
        for p in self.ports:
            self.ports[p].send_packet(json.dumps({'destination': "Broadcast",
                                                         'data': {"name": self.name,
                                                                  "port": self.interface[p],
                                                                 "Hello": 1,
                                                                   "msg": "Hello Request",
                                                              "d_vector": self.distance_vector},
                                                          'hop': 1}).encode())

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
            hop = message["hop"] # N° hops del mensaje
            # Mensaje para el router, solo se lee con _success
            if message['destination'] == self.name:
                self._success(message['data']['msg'])
            # Mensaje Broadcast, debe modificarse el vector de distancia (si es necesario)
            elif message['destination'] == "Broadcast":
                self._success(message['data']['msg'])
                d_vector = message['data']['d_vector'] # Vector de distancia recibido
                name = message["data"]["name"]         # Nombre del enviador
                port = message["data"]["port"]         # Puerto de salida (Interfaz del enviador)
                # Recorremos los nombres del vector de distancia recibidos
                for n in d_vector:
                    # Si un nombre no se encuentra en nuestro vector de distancia o si es menor el camino (RIP min, ya que c(x,y) = 1 para todo x,y)
                    if not(n in self.distance_vector) or (d_vector[n] + hop < self.distance_vector[n]):
                        self.distance_vector[n] = d_vector[n] + hop     # Agregar/modificar el nombre y su distancia + n° de hop de mensaje
                        self.route_table[n] = port                      # Agregar/modificar el nombre del router y el puerto del enviador como output
                        self.dvchanged = True                           # Vector de distancia cambio, se setea True
                # Si es un mensaje broadcast, se notifica a los vecinos el cambio (cuando es Hello no se hace)
                if not(message['data']["Hello"]) and self.dvchanged:
                    self.dvchanged = False                              # Setea falso el booleano
                    self._broadcast()                                   # Envia vector de distancia a vecinos

            else:
                # Si se alcanza el numero maximo de hops
                if hop >= MAX_HOP:
                    self._log("Package has reached maximum hop limit (or the router doesnt exist)")
                else:
                    # Si existe un puerto en la tabla de ruta para el destino, enviar
                    if message['destination'] in self.route_table:
                        port = self.route_table[message['destination']]
                    # Si no, elige uno aleatorio para seguir el viaje
                    else:
                        port = choice(list(self.ports.keys()))
                    self._log("Forwarding to port {}".format(port))
                    message['hop'] += 1
                    self.ports[port].send_packet(json.dumps(message).encode())
        else:
            self._log("Malformed packet")

    # Funcion para actualizar la tabla de ruta a partir de alguna que haya llegado
    #def table_Update(self, new_distanceTable):
        # Revisamos cada nombre en la tabla
    #    for name in self.distance_vector:
    #        distancia = self.distance_vector[name]
    #        if distancia != new_distanceTable[name]:
    #            self.route_distance[name] = min(distancia , ...)

    def _broadcast(self):
        """
        Internal method to broadcast
        :return: None
        """
        self._log("Broadcasting")
        #self._log(self.distance_vector) # Opcional para ver el vector de distancia enviado
        for p in self.ports:
            self.ports[p].send_packet(json.dumps({'destination': "Broadcast",
                                                         'data': {"name": self.name,
                                                                  "port": self.interface[p],
                                                                "Hello" : 0,
                                                                  "msg" : "Update Broadcast",
                                                              "d_vector": self.distance_vector},
                                                          'hop': 1}).encode())
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
