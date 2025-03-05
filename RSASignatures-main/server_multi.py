pip install cryptography


import selectors
import socket
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes



HOST = 'csx3.ucalgary.ca'
PORT = 50007

sel = selectors.DefaultSelector()

#Generate signature key
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def serialize_response(response):
    serialized_response = json.dumps(response)
    return serialized_response.encode('utf-8')

def sign_message(message):
    message_bytes = message.encode('utf-8')
    signature = private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
    )
    return signature.hex()


def accept(sock, mask):
    conn, addr = sock.accept()
    print('accepted', conn, 'from', addr)
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, read)

def read(conn, mask):
    data = conn.recv(1000)
    if data:
        data_json = json.loads(data)
        if data_json["cmd"] == "Sign":
            signature = sign_message(data_json["message"])
            response = {_type": "cmd-response", "signature": signature}
        print('echoing', response, 'to', conn)
        conn.send(serialize_response(response))
    else:
        print('closing', conn)
        sel.unregister(conn)
        conn.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #use for debugging. reuse the port.
    s.bind((HOST, PORT))
    s.listen()
    s.setblocking(False)
    sel.register(s, selectors.EVENT_READ, accept)
    while True:
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

main()

