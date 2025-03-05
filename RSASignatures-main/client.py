import socket
import json

HOST = 'csx3.ucalgary.ca'
PORT = 50007




def verify_signature(___key, message):
    #
    pass

def do_something_with_data(data):
    #look at how the server deals with
    #data that it reads
    pass


#Input json object, outputs flattend
#json object in bytes.
def serialize_request(request):
    serialized_request = json.dumps(request)
    return serialized_request.encode('utf-8')


def main():


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST,PORT))
        request_key = {"cmd":"getKey"}
        s.sendall(serialize_request(request_key))
        request_signature = {"cmd": "Sign", "message": "Greetings"}
        s.sendall(serialize_request(request_signature))
        data = s.recv(1024)

    do_something_with_data(data)
    print('Received', repr(data))

main()
