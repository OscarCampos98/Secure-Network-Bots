# Secure Network Bots
> Python networking project with authenticated command bots (NC + IRC) and a controller.  

This project implements simple **network bots** that connect to a server (TCP or IRC),  
listen for **authenticated commands**, and execute actions such as reporting status,  
moving to a new server, simulating attacks, and shutting down gracefully.  

It was developed as part of a computer security course to practice **socket programming,  
message authentication, and resilient command execution**.  

---

## Features
- **Authentication:** Nonce + SHA-256 based MAC (first 8 hex chars).  
- **Bot behaviors:**
  - `status` → reports nickname and number of commands processed.  
  - `shutdown` → disconnects gracefully.  
  - `move <host:port>` → reconnects to a new server.  
  - `attack <host:port>` → attempts a TCP connect + send, reports OK/FAIL.  
- **Resilience:** Bots reconnect automatically if disconnected.  
- **Controller:** Interactive CLI for issuing commands, aggregating bot responses.  
- **IRC Support:** IRC bot variant joins a channel and accepts commands via chat.  

---

## Components
- **`ncbot.py`** — TCP bot. Connects to a server, executes commands, authenticates with nonce+MAC.  
- **`nccontroller.py`** — Controller. Interactive prompt (`cmd>`) to send commands and process responses.  
- **`ircbot.py`** — IRC bot. Joins a channel, listens for commands, responds in-channel.  

---

## Usage

### 1. NC Bot + Controller (local TCP server)
Run a simple TCP server (e.g. `nc -l 6667`) then start bots and controller:

```bash
# Bot
./ncbot.py localhost:6667 myBot superSecret

# Controller
./nccontroller.py localhost:6667 superSecret
```
Controler prompt:
```bash
cmd> status
cmd> attack localhost:80
cmd> move otherhost:6667
cmd> shutdown
cmd> quit
```
### 2. IRC Bot

```bash
./ircbot.py "irc.example.net:6667" "#myChannel" superSecret
```

Send commands in the channel, for example:

12345678 abcd1234 status
12345678 abcd1234 attack example.com:80

Command Authentication
All commands must be signed with a nonce + secret:
MAC = sha256(nonce + secret)[:8]



### Notes
- The "attack" is a safe connect+send simulation with a 3-second timeout — no real malicious payloads.
- Written for Python 3.
- Developed for CPSC 526 (Computer Security) coursework.
