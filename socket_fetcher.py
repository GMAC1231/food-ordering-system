import socket

def fetch_data_from_socket():
    try:
     
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server = 'data.pr4e.org'
        port = 80
        sock.connect((server, port))

       
        cmd = 'GET http://data.pr4e.org/romeo.txt HTTP/1.0\r\n\r\n'.encode()
        sock.send(cmd)

       
        response = b""
        while True:
            data = sock.recv(512)
            if not data:
                break
            response += data

        sock.close()

        return response.decode()

    except Exception as e:
        return f"Error fetching socket data: {e}"
