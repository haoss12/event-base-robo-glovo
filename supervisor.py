import socket
import json
import time
import select
import sys
from statemachine import StateMachine, State
import numpy as np

class RobotSM(StateMachine):
    wait_in_field = State()
    travel_to_restaurant = State()
    wait_in_restaurant = State()
    travel_to_client = State()
    wait_in_client = State()
    travel_to_base = State()
    wait_in_base = State(initial=True)
    dead = State(final=True)

    robot_spawn = wait_in_base.to(wait_in_field, after='robot_spawn')
    robot_return = wait_in_field.to(travel_to_base, after='robot_return')
    robot_returned = travel_to_base.to(wait_in_base, after='robot_returned')

    robot_pick1 = wait_in_field.to(travel_to_restaurant, after='robot_pick1')
    robot_arrived = travel_to_restaurant.to(wait_in_restaurant, after='robot_arrived')
    robot_pick2 = wait_in_restaurant.to(travel_to_restaurant, after='robot_pick2')
    robot_deliver1 = wait_in_restaurant.to(travel_to_client, after='robot_deliver1')
    food_delivered = travel_to_client.to(wait_in_client, after='food_delivered')
    robot_deliver2 = wait_in_client.to(travel_to_client, after='robot_deliver2')
    robot_empty = wait_in_client.to(wait_in_field, after='robot_empty')

    battery_dead1 = travel_to_restaurant.to(dead, after='battery_dead1')
    battery_dead2 = travel_to_client.to(dead, after='battery_dead2')
    battery_dead3 = travel_to_base.to(dead, after='battery_dead3')

    def on_enter_state(self, target, event):
        print(f"robot: entering {target} from {event}")

class Robot:
    id = 0

    def __init__(self, supervisor):
        self.id = Robot.id
        self.supervisor = supervisor
        self.sm = RobotSM()
        Robot.id +=1
        self.battery_low = False
        self.position = [0, 0]

    def send(self, event):
        if event=='robot_pick' and self.sm.current_state.name=='Wait in field':
            event = 'robot_pick1'

        if event=='robot_pick' and self.sm.current_state.name=='Wait in restaurant':
            event = 'robot_pick2'

        if event=='robot_deliver' and self.sm.current_state.name=='Wait in restaurant':
            event = 'robot_deliver1'

        if event=='robot_deliver' and self.sm.current_state.name=='Wait in client':
            event = 'robot_deliver2'

        if event=='battery_dead' and self.sm.current_state.name=='Travel to restaurant':
            event = 'battery_dead1'

        if event=='battery_dead' and self.sm.current_state.name=='Travel to client':
            event = 'battery_dead2'

        if event=='battery_dead' and self.sm.current_state.name=='Travel to base':
            event = 'battery_dead3'

        try:
            self.sm.send(event)
        except:
            pass

    def feed_event(self, event):
        if 'robot_number' in event:
            if event['robot_number']==self.id:
                self.send(event['id'])

                match event['id']:
                    case 'battery_low':
                        self.battery_low = True
                    case 'robot_arrived':
                        orders = [order for order in self.supervisor.orders if order.robot.id==self.id]

                        #TODO consider all orders for this robot
                        order = orders[0]
                        if order.sm.current_state.name=='Wait for deliver':
                            self.position = order.address
                            self.supervisor.transmit({
                                'id': 'robot_deliver',
                                'robot_number': self.id,
                                'food': order.food,
                                'address': order.address,
                                'order_number': order.id,
                            })

                match self.sm.current_state.name:
                    case 'Wait in base':
                        self.battery_low = False
                        self.position = [0, 0]
                    case 'Wait in field':
                        if self.battery_low:
                            self.position = [0, 0]
                            self.supervisor.transmit({
                                'id': 'robot_return',
                                'robot_number': self.id,
                            })

        else:
            match event['id']:
                case 'food_delivered':
                    orders = [order for order in self.supervisor.orders if order.robot.id==self.id]

                    if(len(orders)>0):
                        self.send('food_delivered')

class OrderSM(StateMachine):
    initial = State(initial=True)
    wait_for_food = State()
    wait_for_pick = State()
    wait_for_deliver = State()
    finished = State(final=True)

    food_start = initial.to(wait_for_food, after='food_start')
    food_ready = wait_for_food.to(wait_for_pick, after='food_ready')
    food_picked = wait_for_pick.to(wait_for_deliver, after='food_picked')
    food_delivered = wait_for_deliver.to(finished, after='food_delivered')

    def on_enter_state(self, target, event):
        print(f'order: entering {target} from {event}')

class Order:
    def __init__(self, supervisor, id, food, restaurant, address):
        self.sm = OrderSM()
        self.supervisor = supervisor
        self.id = id
        self.food = food
        self.restaurant = restaurant
        self.address = address

    def send(self, event):
        try:
            self.sm.send(event)
        except:
            pass

    def feed_event(self, event):
        match event['id']:
            case 'food_start':
                self.send(event['id'])
            case 'robot_returned':
                pass
            case 'robot_arrived':
                pass
            case 'food_delivered':
                if event['order_number']==self.id:
                    self.send(event['id'])
            case 'robot_empty':
                pass
            case 'food_ready':
                if event['order_number']==self.id:
                    self.send(event['id'])

                if self.robot.sm.current_state.name=='Wait in restaurant':
                    print("----------------- Potezny DUPA PRINT ----------------")
                    self.supervisor.transmit({
                        'id': 'robot_deliver',
                        'robot_number': self.robot.id,
                        'food': self.food,
                        'address': self.address,
                        'order_number': self.id,
                    })
            case 'food_picked':
                if event['order_number']==self.id:
                    self.send(event['id'])
                    self.supervisor.transmit({
                        'id': 'robot_deliver',
                        'robot_number': self.robot.id,
                        'food': self.food,
                        'address': self.address,
                        'order_number': self.id,
                    })

        match self.sm.current_state.name:
            case 'Initial':
                self.supervisor.transmit({
                    'id': 'food_start',
                    'order_number': self.id,
                    'food': self.food,
                    'restaurant': self.restaurant,
                })

                waiting_robots = [robot for robot in self.supervisor.robots if robot.sm.current_state.name=='Wait in field' or robot.sm.current_state.name=='Wait in base']

                if len(waiting_robots)>0:
                    field_robots = [robot for robot in self.supervisor.robots if robot.sm.current_state.name=='Wait in field']

                    if len(field_robots)==0:
                        self.supervisor.transmit({
                            'id': 'robot_spawn',
                        })
                        field_robots = [robot for robot in self.supervisor.robots if robot.sm.current_state.name=='Wait in field']

                    min_dist = 1000000
                    for robot in field_robots:
                        dist = np.abs(robot.position[0] - self.restaurant[0]) + np.abs(robot.position[1] - self.restaurant[1])
                        if dist<min_dist:
                            self.robot = robot
                            min_dist = dist

                    self.robot.position = self.restaurant
                    self.supervisor.transmit({
                        'id': 'robot_pick',
                        'robot_number': self.robot.id,
                        'order_number': self.id,
                        'food': self.food,
                        'restaurant': self.restaurant,
                    })

    def is_finished(self):
        return self.sm.current_state.name=='Finished'

class Communication:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)
        self.connected = False
        self.attempt_connection()

    def attempt_connection(self):
        attempt_count = 0
        while not self.connected:
            try:
                self.socket.connect((self.host, self.port))
                self.connected = True
                print("Connected to Simulation.")
            except socket.error as e:
                if e.errno == socket.errno.EINPROGRESS or e.errno == socket.errno.EALREADY:
                    print("Non-blocking connect in progress...")
                    if self.complete_connection():
                        break
                elif e.errno == socket.errno.EISCONN:
                    self.connected = True
                    print("Already connected to Simulation.")
                    break
                elif e.errno == socket.errno.ECONNREFUSED:
                    attempt_count += 1
                    print(f"Connection refused, attempt {attempt_count}. Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    print(f"Unexpected error during connection: {e}")
                    sys.exit(1)

    def complete_connection(self):
        ready_to_write, _, _ = select.select([], [self.socket], [], 5)
        if ready_to_write:
            try:
                self.socket.getpeername()  # An exception will be raised if the socket is not actually connected
                print("Connection successfully established.")
                return True
            except socket.error as e:
                print(f"Failed to establish connection: {e}")
                return False
        return False

    def send_dict(self, data_):
        if not self.connected:
            print("No connection available to send data.")
            return
        try:
            data_to_send = json.dumps(data_)
            self.socket.sendall(data_to_send.encode('utf-8'))
        except (TypeError, ValueError, socket.error) as e:
            print("Error sending data:", str(e))

    def receive_dict(self):
        try:
            ready_to_read, _, _ = select.select([self.socket], [], [], 0.1)
            if ready_to_read:
                data = self.socket.recv(1024).decode('utf-8')
                if data:
                    return json.loads(data)
            return {}
        except (BlockingIOError, socket.timeout):
            return {}
        except (json.JSONDecodeError, socket.error) as e:
            print("Error receiving data:", e)
            return {}

    def close(self):
        self.socket.close()

class Supervisor:
    def __init__(self, host, port):
        with open("simulation/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)

        max_robots = config["max_robots"]

        self.communication = Communication(host, port)
        self.to_send = []
        self.robots = [Robot(self) for _ in range(max_robots)]
        self.orders = []

    def transmit(self, controllable_event):
        #print(f'tx {controllable_event}')

        self.to_send.append(controllable_event)

        if controllable_event['id']=='robot_spawn':
            robots_in_the_base = [robot for robot in self.robots if robot.sm.current_state.name=='Wait in base']

            robot = robots_in_the_base[0]
            robot.send('robot_spawn')
        else:
            self.receive(controllable_event)

    def flush(self):
        if len(self.to_send)>0:
            print(self.to_send)
            self.communication.send_dict(self.to_send)
            self.to_send = []

    def receive(self, event):
        if event['id']=='new_order':
            self.orders.append(Order(self,
                event['order_number'],
                event['food'],
                event['restaurant'],
                event['address']
            ))

        for order in self.orders:
            order.feed_event(event)

        for robot in self.robots:
            robot.feed_event(event)

        self.orders = [order for order in self.orders if not order.is_finished()]

if __name__ == "__main__":
    supervisor = Supervisor('localhost', int(sys.argv[1]))
    try:
        while True:
            received_data = supervisor.communication.receive_dict()
            if received_data:
                print(f'rx {received_data}')
                for msg in received_data:
                    supervisor.receive(msg)
            supervisor.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Shutting down Supervisor.")
    finally:
        supervisor.communication.close()

'''
supervisor = Supervisor('localhost', 12345)

supervisor.receive({
    'id': 'new_order',
    'order_number': 1,
    'food': 5,
    'restaurant': [1, 2],
    'address': [4, 5],
})

supervisor.receive({
    'id': 'robot_arrived',
    'robot_number': 0,
    'restaurant': [1, 2],
})

supervisor.receive({
    'id': 'food_ready',
    'order_number': 1,
    'food': 5,
    'restaurant': [1, 2],
})

supervisor.receive({
    'id': 'food_picked',
    'order_number': 1,
    'food': 5,
    'restaurant': [1, 2],
})

supervisor.receive({
    'id': 'food_delivered',
    'order_number': 1,
    'address': [4, 5],
})

supervisor.receive({
    'id': 'robot_empty',
    'robot_number': 0,
})
'''
