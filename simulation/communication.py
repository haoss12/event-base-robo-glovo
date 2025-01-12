import json
import socket


class Communication:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.client_socket, self.addr = self.socket.accept()
        self.client_socket.setblocking(0)

    def send_data(self, data_):
        try:
            data_to_send = json.dumps(data_)
            self.client_socket.sendall(data_to_send.encode("utf-8"))
        except (TypeError, ValueError, socket.error) as e:
            print("Error:", str(e))

    def receive_dict(self):
        try:
            data = self.client_socket.recv(1024).decode("utf-8")
            if data:
                return json.loads(data)
            return {}
        except BlockingIOError:
            return {}
        except (json.JSONDecodeError, socket.error) as e:
            print("Error:", e)
            return {}

    def run(self, events_to_send):
        self.send_data(events_to_send)
        return self.receive_dict()

    def close(self):
        self.client_socket.close()
        self.socket.close()


if __name__ == "__main__":
    simulation = Communication("localhost", 12345)
    try:
        while True:
            data = simulation.receive_dict()
            if data:
                print("Received from supervisor:", data)
                simulation.send_data({"test 0": "test 123"})
    except KeyboardInterrupt:
        print("Shutting down Simulation.")
    finally:
        simulation.close()
