#!/usr/bin/env python3
import sys
import socket
import time
import hashlib
import select
from socket import gaierror, timeout


# Global variables for the current server
current_hostname = None
current_port = None
sock = None  

def is_hostname_resolvable(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False
    
def parse_command_line_arguments():
    # Parse command line arguments to extract the server hostname, port, bot nickname, and secret.
    if len(sys.argv) != 4:
        print("Usage: ./ncbot.py <hostname:port> <nick> <secret>")
        sys.exit(1)
    hostname, port = sys.argv[1].split(":")
    nick = sys.argv[2]
    secret = sys.argv[3]
    return hostname, int(port), nick, secret

def connect_to_server(hostname, port):
    # Attempt to connect to the specified server. Retry indefinitely on failure.
    global sock
    while True:
        try:
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.connect((hostname, port))
            print("Connected.")
            return new_sock
        except socket.error as e:
            print(f"Failed to connect. Reconnecting in 5s: {e}")
            time.sleep(5)
        

#similar to python socket protocol
def send_data(sock, data):
    total_sent = 0
    while total_sent < len(data):
        try:
            sent = sock.send(data[total_sent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent
        except socket.error as e:
            print(f"Send error: {e}")
            raise
#similar to python socket protocol
def recv_data(sock, bufsize=1024):
    try:
        data = sock.recv(bufsize)
        if data == b'':
            raise RuntimeError("socket connection broken")
        return data
    except socket.error as e:
        print(f"Receive error: {e}")
        raise


def authenticate_command(nonce, secret, mac):
    # Compute the MAC for the nonce+secret and compare it with the provided MAC.
    expected_mac = hashlib.sha256(f"{nonce}{secret}".encode()).hexdigest()[:8]
    return mac == expected_mac

def attack(hostname, port, nick, nonce, bot_sock):
    
    report_message = ""
    
    # Check if the hostname is resolvable
    if not is_hostname_resolvable(hostname):
        report_message = f"-attack {nick} FAIL no such hostname\n"
        send_data(bot_sock, report_message.encode())
        return

    attack_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    attack_sock.setblocking(0)  
    try:
        attack_sock.connect((hostname, port))
    except BlockingIOError:
        pass  

    # Use select to monitor the socket for readiness to write or errors for up to 3 seconds
    try:
        _, ready_to_write, in_error = select.select([], [attack_sock], [attack_sock], 3)
        if ready_to_write:
            attack_msg = f"{nick} {nonce}\n".encode()
            attack_sock.sendall(attack_msg)
            report_message = f"-attack {nick} OK\n"
        else:
            report_message = f"-attack {nick} FAIL Timeout or Unable to Connect\n"
    except Exception as e:
        report_message = f"-attack {nick} FAIL {str(e)}\n"
    finally:
        attack_sock.close()
        send_data(bot_sock, report_message.encode())

#Handles moving the bot to a new server specified by the new_host and new_port arguments.    
def move_to_new_server(new_host, new_port, nick, secret):
    global current_hostname, current_port, sock

    # Notify server of move, if the socket exists
    if sock:
        try:
            send_data(sock, f"-move {nick}\n".encode())
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except socket.error as e:
            print(f"Error closing old socket: {e}")
    else:
        print("No active socket to close.")

    sock = None  # Reset the socket to trigger reconnection
    current_hostname, current_port = new_host, new_port  # Fix the typo here
   

def listen_for_commands(nick, secret):
    global sock, current_hostname, current_port
    seen_nonces = set()
    command_count = 0
    while True:

        if not sock:
            sock = connect_to_server(current_hostname, current_port)
            send_data(sock, f"-joined {nick}\n".encode())

        try:
            data = recv_data(sock, 1024).decode().strip()
            if not data:
                print ("Server Disconected ")
                sock = None
                continue

            # Check if the message is a system/join message and not a command.
            if data.startswith("-joined"):
                joined_nick = data.split()[1]
                # Check if the join message is from another bot.
                if joined_nick != nick:  
                    print(f"{joined_nick} has joined.")
                continue  

            # Check if the message is a report from an attack if so skipped.
            if any(data.startswith(prefix) for prefix in ["-attack", "-status", "-shutdown", "-move"]):
                
                continue
            
            #check the format of the responce from the server
            parts = data.split()
            if len(parts) < 3:
                print(f"Invalid command format: {data}")
                continue
            
            #format of the command send by the server 
            authenticate_nonce, mac, command, *args = parts

            # Verify nonce uniqueness and command authenticity
            if authenticate_nonce in seen_nonces or not authenticate_command(authenticate_nonce, secret, mac):
                print(f"Invalid or duplicate nonce detected: {authenticate_nonce}. Ignoring command.")
                continue
            seen_nonces.add(authenticate_nonce)

            # Execute recognized commands or print a message for unrecognized ones
            if command in ["status", "shutdown", "move", "attack"]:
                command_count += 1
                execute_command(authenticate_nonce, command, args, sock, nick, command_count, secret)
            else:
                wrong_command = f"The command '{command}' is not accepted."
                print(wrong_command)
                send_data(sock, wrong_command.encode())
        except RuntimeError as e:
            print(f"Error or disconnection detected: {e}")
            
            # Reset the socket to trigger a reconnection attempt
            sock = None  
            break
            

def execute_command(authenticate_nonce ,command, args, sock, nick, command_count, secret):
    print(f"Executing command: {command}, Args: {args}")

    # Debugging output for any command received, showing expected authentication info
    if command != "status" and command != "shutdown":
        expected_mac = hashlib.sha256(f"{authenticate_nonce}{secret}".encode()).hexdigest()[:8]
        print(f"Debug: Command: {command}, Nonce: {authenticate_nonce}, Expected MAC: {expected_mac}\n")
    
    if command == "status":
        response = f"-status {nick} {command_count}\n"
        send_data(sock, response.encode())
        
    elif command == "shutdown":
        response = f"-shutdown {nick}\n"
        send_data(sock, response.encode())
        # Shutdown the socket for both reading and writing.
        sock.shutdown(socket.SHUT_RDWR)  
        sock.close()  
        sys.exit(0)  
    
    elif command == "attack":
        if len(args) == 1:
            attack_hostname, attack_port = args[0].split(":")
            attack(attack_hostname, int(attack_port), nick, authenticate_nonce, sock)
        else:
            print("Invalid arguments for the attack command.")
    
    elif command == "move":
        if len(args) != 1:
            print("Invalid move command format.")
            return
        new_host, new_port_str = args[0].split(":")
        try:
            new_port = int(new_port_str)
            move_to_new_server(new_host, new_port, nick, secret)  
        except ValueError:
            print("Invalid port number provided for move command.")    

def main():
    global current_hostname, current_port, sock

    current_hostname, current_port, nick, secret = parse_command_line_arguments()

    while True:
        try:
            if not sock:
                sock = connect_to_server(current_hostname, current_port)
                send_data(sock, f"-joined {nick}\n".encode())
            listen_for_commands(nick, secret)
        except KeyboardInterrupt:
            print("Program has been exited.")
            break
        except Exception as e:
            print(f"Unexpected error, trying to reconnect: {e}")
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass 
            # Reset sock to None to allow reconnection attempts     
            sock = None  
            time.sleep(5)

        

if __name__ == "__main__":
    main()
