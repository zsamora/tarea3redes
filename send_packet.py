import socket


def send_packet(port, message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', port)
    # TODO: formateo de paquetes
    try:
        sock.sendto(message.encode(), server_address)
    finally:
        sock.close()
