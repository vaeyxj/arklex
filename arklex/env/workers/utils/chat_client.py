"""
This module is currently inactive.

It is reserved for future use and may contain experimental or planned features.

Status:
    - Not in use (as of 2025-02-20)
    - Intended for future feature expansion

Module Name: chat_client

This file contains the code for setting up a chat client that can connect to a chat server and send and receive messages.
"""

import sys
import asyncio
import json
import argparse

import threading
from concurrent.futures import Future

# Shared future for async result
async_result = Future()

class ChatClient:
    ''' Chat client class '''
    reader, writer = None, None
    
    def __init__(self, server_address='127.0.0.1', server_port='8888', *, name=None, mode='c', debug=False):
        self.server_address = server_address
        self.server_port = server_port
        self.name = name
        self.mode = mode
        
        self.timeout = 100000
        self.debug = debug
        
        self.logs = []
        
        self.async_thread = None
        self.async_result = Future()
    
    # Thread for async event loop
    def async_thread_worker(self, message: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(self.main(message))
        self.async_result.set_result(result)
        
    def sync_main(self, message: str=None) -> str:
        self.async_thread = threading.Thread(target=self.async_thread_worker, args=(message,))
        self.async_thread.start()
        return self.async_result.result()
    
    def format_logs(self, logs: list[dict]) -> str:
        return '\n'.join([f"{log['name']}: {log['message']}" for log in logs])
        
    async def send_message(self, message):
        msg_bytes = json.dumps({'name': self.name, 'message': message}).encode()
        # transmit the message to the server
        self.writer.write(msg_bytes)
        # wait for the buffer to be empty
        await self.writer.drain()
            
        
    # send message to server
    async def write_messages(self):
        # read messages from the user and transmit to server
        while True:
            # read from stdin
            message = await asyncio.to_thread(sys.stdin.readline)
            
            # clear the input line
            CURSOR_UP = '\033[F'
            ERASE_LINE = '\033[K'
            print(CURSOR_UP + ERASE_LINE + CURSOR_UP)
            sys.stdout.flush()
            
            await self.send_message(message)
                
            # check if the user wants to quit the program
            if message.strip() == 'QUIT':
                # exit the loop
                break
            
        # report that the program is terminating
        print('Quitting...')
        
    async def receive_message(self):
        result_bytes = await self.reader.read(1024)  # Read raw bytes
        decoded_data = result_bytes.decode()
        messages = []
        # print(decoded_data)
        for data in decoded_data.split('{'):
            if not data:
                continue
            
            # convert to string
            # data_json = json.loads('{' + data)
            # name, line = data_json['name'], data_json['message'].strip()
            result_json = json.loads('{' + data)
            if self.debug or (self.mode == 'c' and result_json['name'] != 'Server'):
                print(f"{result_json['name']}: {result_json['message'].strip()}")
            messages.append(result_json)
            
        return messages
        
    # read messages from the server
    async def read_messages(self):
        # read messages from the server and print to user
        while True:
            messages = await self.receive_message()
            self.logs.extend(messages)
    
    # echo client
    async def main(self, message=None):
        # report progress to the user
        if self.debug:
            print(f'Connecting to {self.server_address}:{self.server_port}...')
        # open a connection to the server
        self.reader, self.writer = await asyncio.open_connection(self.server_address, self.server_port)
        # report progress to the user
        if self.debug:
            print('Connected.')
        
        if not self.name:
            self.name = input("Enter name: ")
        
        connect = {"sys": "connect", "name": self.name}
        connect_json = json.dumps(connect)
        self.writer.write(connect_json.encode())
        await self.writer.drain()
        
        await self.receive_message()
        await self.receive_message()
        
        read_task, write_task = None, None
        
        match self.mode:
            case 'c':
                # read and report messages from the server
                read_task = asyncio.create_task(self.read_messages())
                
                # write messages to the server
                write_task = asyncio.create_task(self.write_messages())
                    
                # wait for either task to complete
                done, pending = await asyncio.wait(
                    [read_task, write_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                
                # cancel the remaining tasks
                for task in pending:
                    task.cancel()
                    
                await self.writer.drain()
                # report progress to the user
                print('Disconnecting from server...')
                # close the stream writer
                self.writer.close()
                # wait for the tcp connection to close
                await self.writer.wait_closed()
                # report progress to the user
                print('Done.')
                return self.format_logs(self.logs)

            case 'ro':
                if message: 
                    await self.send_message(message)
                read_msg = None
                while not read_msg:
                    for m in await self.receive_message():
                        if m['name'] != 'Server' and m['name'] != self.name:
                            read_msg = m['message']
                await self.send_message("QUIT")
                return read_msg
            
            case 'wo':
                await self.send_message(message)
                await self.send_message("QUIT")
                return None
                
            case _:
                raise ValueError(f"Invalid mode: {self.mode}")
            
        
        # report progress to the user
        print('Disconnecting from server...')
        # close the stream writer
        self.writer.close()
        # wait for the tcp connection to close
        await self.writer.wait_closed()
        # report progress to the user
        print('Done.')
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-address', type=str, default='127.0.0.1')
    parser.add_argument('--server-port', type=int, default=8888)
    parser.add_argument('--name', type=str, default='User')
    parser.add_argument('--timeout', type=int, default=100000)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--mode', default='c', choices=['c', 'ro', 'wo'])
    parser.add_argument('--message', type=str, default=None)
    args = parser.parse_args()
    
    # create the chat client
    client = ChatClient(
                server_address=args.server_address, 
                server_port=args.server_port, 
                name=args.name, 
                mode=args.mode, 
                debug=args.debug
            )
    # run the event loop
    asyncio.run(client.main(args.message))
    