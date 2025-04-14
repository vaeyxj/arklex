"""
This module is currently inactive.

It is reserved for future use and may contain experimental or planned features.

Status:
    - Not in use (as of 2025-02-20)
    - Intended for future feature expansion

Module Name: chat_server

This file contains the code for setting up a chat server that can accept connections from chat clients and broadcast messages to all connected clients.
"""

import asyncio
import json
import sys

import argparse

class ChatServer:
    ''' Chat server class '''
    
    # dict of all current users
    ALL_USERS = {}
    SERVER_USER = 'Server'
    
    def __init__(self, host_address, host_port):
        self.host_address = host_address
        self.host_port = host_port
        
    # write a message to a stream writer
    async def write_message(self, writer, msg_bytes):
        # write message to this user
        writer.write(msg_bytes)
        # wait for the buffer to empty
        await writer.drain()
    
    # send a message to all connected users
    async def broadcast_message(self, name, message: str=''):
        # report locally
        
        print(f'{name}: {message.strip()}')
        sys.stdout.flush()
        msg_bytes = json.dumps({'name': name, 'message': message}).encode()
        # enumerate all users and broadcast the message
        
        # create a task for each write to client
        tasks = [asyncio.create_task(self.write_message(w, msg_bytes)) for _,(_,w) in self.ALL_USERS.items()]
        # wait for all writes to complete
        if tasks: 
            _ = await asyncio.wait(tasks)
    
    # connect a user
    async def connect_user(self, reader: asyncio.StreamWriter, writer: asyncio.StreamWriter):
        # ask the user for their name
        data = await reader.read(1024)  # Read raw bytes
        # print(data)
        # convert name to string
        name = json.loads(data.decode())['name']
        # store the user details
        self.ALL_USERS[name] = (reader, writer)
        # announce the user
        await self.broadcast_message(self.SERVER_USER, f'{name} has connected\n')
        # welcome message
        await self.write_message(writer, json.dumps({'name': self.SERVER_USER, 'message':  f'Welcome {name}. Send QUIT to disconnect.'}).encode())
        return name
    
    # disconnect a user
    async def disconnect_user(self, name: str, writer: asyncio.StreamWriter):
        # close the user's connection
        writer.close()
        await writer.wait_closed()
        # remove from the dict of all users
        del self.ALL_USERS[name]
        # broadcast the user has left
        await self.broadcast_message(self.SERVER_USER, f'{name} has disconnected\n')
    
    # handle a chat client
    async def handle_chat_client(self, reader: asyncio.StreamWriter, writer: asyncio.StreamWriter):
        print('Client connecting...')
        # connect the user
        name = await self.connect_user(reader, writer)
        try:
            # read messages from the user
            while True:
                # read data
                data = await reader.read(1024)  # Read raw bytes
                decoded_data = data.decode()
                sys.stdout.flush()
                for data in decoded_data.split('{'):
                    if not data:
                        continue
                    
                    # convert to string
                    data_json = json.loads('{' + data)
                    name, line = data_json['name'], data_json['message'].strip()
                    # check for exit
                    if line == 'QUIT':
                        break
                    # broadcast message
                    await self.broadcast_message(name, line)
                else:
                    continue
                break
        finally:
            # disconnect the user
            await self.disconnect_user(name, writer)
    
    # chat server
    async def main(self):
        # define the local host
        # create the server
        server = await asyncio.start_server(self.handle_chat_client, self.host_address, self.host_port)
        # run the server
        async with server:
            # report message
            print('Chat Server Running\nWaiting for chat clients...')
            # accept connections
            await server.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-address', type=str, default='127.0.0.1')
    parser.add_argument('--server-port', type=int, default=8888)
    args = parser.parse_args()
    
    server = ChatServer(args.server_address, args.server_port)
    # start the event loop
    asyncio.run(server.main())