import socket
import threading
import logging

from time import sleep

# Initialize a lock for thread-safe access to the connection pool
conn_map_lock = threading.Lock()
# Initialize the connection pool as a dictionary
connection_pool = {}

# Example usage
# tcp_dial(b"Hello, world", "192.168.1.1")
def tcp_dial(context, addr):
    global connection_pool

    with conn_map_lock:
        # Check if the connection already exists in the pool
        if addr not in connection_pool:
            try:
                # Create a new TCP connection
                conn = socket.create_connection((addr, 80))  # Assuming port 80, modify as needed
                connection_pool[addr] = conn
            except socket.error as e:
                logging.error(f"Connect error: {e}")
                return

        conn = connection_pool[addr]

    try:
        # Send the context data with a newline character at the end
        conn.sendall(context + b'\n')
    except socket.error as e:
        # Handle potential write errors
        logging.error(f"Error sending data: {e}")

# Usage Example
# Suppose the sender has IP '192.168.1.1' and wants to broadcast a message to two other IPs.
# sender_ip = '192.168.1.1'
# receivers_ips = ['192.168.1.2', '192.168.1.3']
# message = b"Hello, this is a broadcast message"
# broadcast(sender_ip, receivers_ips, message)
def broadcast(sender, receivers, msg):
    """
    Sends a message to all receivers except the sender.

    Parameters:
    sender (str): The IP address of the sender to exclude from broadcasting.
    receivers (list of str): The list of receiver IP addresses.
    msg (bytes): The message to be sent in bytes.
    """

    def dial(receiver):
        # Skip sending to the sender itself
        if receiver != sender:
            tcp_dial(msg, receiver)

    # Start a new thread for each receiver
    for ip in receivers:
        thread = threading.Thread(target=dial, args=(ip,))
        thread.start()

# Usage Example
# To close all connections in the pool, simply call the function without any arguments.
# close_all_conn_in_pool()
def close_all_conn_in_pool():
    """
    Closes all the connections in the connection pool and clears the pool.
    """

    global connection_pool

    with conn_map_lock:
        # Close each connection in the pool
        for conn in connection_pool.values():
            conn.close()
        # Clear the connection pool after closing all connections
        connection_pool.clear()


