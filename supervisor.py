import socket
import json
import time
import select
import sys
from statemachine import StateMachine, State

class RobotSM(StateMachine):
    wait_in_field = State()
    travel_to_restaurant = State()
    wait_in_restaurant = State()
    travel_to_client = State()
    wait_in_client = State()
    travel_to_base = State()
    wait_in_base = State(initial=True)

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

    def on_enter_state(self, target, event):
        print(f"robot: entering {target} from {event}")

class Robot:
    id = 0

    def __init__(self, supervisor):
        self.id = Robot.id
        self.supervisor = supervisor
        self.sm = RobotSM()
        Robot.id +=1

    def send(self, event):
        #print(self.sm.current_state.name, event)

        if event=='robot_pick' and self.sm.current_state.name=='Wait in field':
            event = 'robot_pick1'

        if event=='robot_pick' and self.sm.current_state.name=='Wait in restaurant':
            event = 'robot_pick2'

        if event=='robot_deliver' and self.sm.current_state.name=='Wait in restaurant':
            event = 'robot_deliver1'

        if event=='robot_deliver' and self.sm.current_state.name=='Wait in client':
            event = 'robot_deliver2'

        try:
            self.sm.send(event)
        except:
            #print('poraszka')
            pass

    def feed_event(self, event):
        if 'robot_number' in event:
            if event['robot_number']==self.id:
                self.send(event['id'])
                #print(f'co jest {self.id} {event}')

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
            case 'food_picked':
                if event['order_number']==self.id:
                    self.send(event['id'])

        match self.sm.current_state.name:
            case 'Initial':
                self.supervisor.transmit({
                    'id': 'food_start',
                    'food': self.food,
                    'restaurant': self.restaurant,
                })

                available_robots = [robot for robot in self.supervisor.robots if robot.sm.current_state.name=='Wait in field']

                #print([robot.id for robot in available_robots])

                if len(available_robots)>0:
                    self.robot = available_robots[0] #TODO make better choice of robot
                else:
                    self.supervisor.transmit({
                        'id': 'robot_spawn',
                    })

                    available_robots = [robot for robot in self.supervisor.robots if robot.sm.current_state.name=='Wait in field']

                    self.robot = available_robots[0] #TODO make better choice of robot

                self.supervisor.transmit({
                    'id': 'robot_pick',
                    'robot_number': self.robot.id,
                    'food': self.food,
                    'restaurant': self.restaurant,
                })

    def is_finished(self):
        return self.sm.current_state.name=='Finished'

class Supervisor:
    def __init__(self, host, port):
        self.robots = [Robot(self) for _ in range(3)]
        self.orders = []

    def transmit(self, controllable_event):
        print(f'transmit {controllable_event}')

        if controllable_event['id']=='robot_spawn':
            robots_in_the_base = [robot for robot in self.robots if robot.sm.current_state.name=='Wait in base']

            robot = robots_in_the_base[0]
            robot.send('robot_spawn')
        else:
            self.receive(controllable_event)

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

supervisor = Supervisor('localhost', 12345)

supervisor.receive({
    'id': 'new_order',
    'order_number': 1,
    'food': 5,
    'restaurant': [1, 2],
    'address': [4, 5],
})

supervisor.receive({
    'id': 'new_order',
    'order_number': 2,
    'food': 5,
    'restaurant': [1, 2],
    'address': [4, 5],
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
    'food': 5,
    'restaurant': [1, 2],
    'address': [4, 5],
})

print(len(supervisor.orders))

#while True:
#    supervisor.send_dict({"message": 'Hello Simulation'})
#    received_data = supervisor.receive_dict()
#    time.sleep(1)
