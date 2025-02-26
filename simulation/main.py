import json
import os
import random
import sys
from collections import deque
from enum import Enum

import pygame

from communication import Communication
from render import Renderer


class Objective(Enum):
    IDLE = 0
    PICKING_UP = 1
    WAITING_FOR_FOOD_TO_BE_READY = 2
    GOING_WITH_ORDER = 3
    RETURNING_TO_BASE = 4

# Event Types
DEBUG: bool = False


class EventType(Enum):
    NEW_ORDER = "new_order"
    SPAWN_COURIER = "robot_spawn"
    ID_OF_SPAWNED_ROBOT = "id_of_spawned_robot"
    RETURN_TO_BASE = "robot_return"
    ARRIVED_AT_BASE = "robot_returned"
    LOW_BATTERY_WARNING = "battery_low"
    BATTERY_DEPLETED = "battery_dead"
    ARRIVED_AT_RESTAURANT = "robot_arrived"
    ROBOT_PICK_FOOD = "robot_pick"
    FOOD_PICKED_UP = "food_picked"
    FOOD_READY = "food_ready"
    DELIVER_FOOD = "robot_deliver"
    FOOD_DELIVERED = "food_delivered"
    BACKPACK_EMPTIED = "robot_empty"  # "plecak_skurwiela_oprozniony"
    FOOD_START = "food_start"


class Robot:
    def __init__(self, robot_id, x, y, battery_range, backpack_capacity, event_queue, road_spacing):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        # zasięg na baterii (np. liczba "kroków")
        self.battery_range = battery_range
        self.current_battery_range = battery_range
        self.backpack_capacity = backpack_capacity
        self.current_capacity = 0
        self.target_x = None
        self.target_y = None
        self.current_objective = Objective.IDLE
        self.event_queue: EventQueue = event_queue  # Reference to the event queue
        self.orders = {}
        self.deliveries = {}
        self.restaurant_at_which_robot_waits = []
        self.road_spacing = road_spacing

    def set_target(self, tx, ty, type: Objective):
        self.target_x = tx
        self.target_y = ty
        self.current_objective = type

    def add_order(self, restaurant, order_number, food):
        self.orders[order_number] = {"restaurant": restaurant, "ready_flag": False, "food": food}

    def add_delivery(self, address, order_number, food):
        self.deliveries[order_number] = {"address": address, "food": food}

    def set_order_ready(self, order_number):
        self.orders[order_number]["ready_flag"] = True

    def pickup_food(self, restaurant):
        """Add food to backpack, simulating pickup of an order from restaurant"""
        order_to_remove_from_dict = -1
        for order_number, order_param in self.orders.items():
            restaurant_location = order_param["restaurant"]
            if restaurant_location != restaurant:
                continue

            if order_param["ready_flag"]:
                food_capacity = order_param["food"]["size"]
                if (self.current_capacity + food_capacity) > self.backpack_capacity:
                    raise Exception(
                        f"Supervisor exceeded max capacity for robot #{self.robot_id}")
                self.current_capacity += food_capacity
                self.event_queue.enqueue({
                    "id": EventType.FOOD_PICKED_UP.value,
                    "order_number": order_number,
                    "food": order_param["food"],
                    "restaurant": restaurant,
                })
                self.current_objective = Objective.IDLE
                self.restaurant_at_which_robot_waits = []
                order_to_remove_from_dict = order_number

            else:
                self.current_objective = Objective.WAITING_FOR_FOOD_TO_BE_READY
                self.restaurant_at_which_robot_waits = restaurant
        if order_to_remove_from_dict >= 0:
            del self.orders[order_to_remove_from_dict]

    def give_food(self, address):
        """Remove food from backpack, simulating giving order to customer"""
        delivery_to_remove_from_dict = -1
        for order_number, delivery_parameters in self.deliveries.items():
            destination = delivery_parameters["address"]
            if destination != address:
                continue

            removed_capacity = delivery_parameters["food"]["size"]
            self.current_capacity -= removed_capacity
            delivery_to_remove_from_dict = order_number

            self.event_queue.enqueue({
                "id": EventType.FOOD_DELIVERED.value,
                "order_number": order_number,
                "address": address,
            })

            # Generate event: Backpack emptied
            if self.current_capacity == 0:
                self.event_queue.enqueue({
                    "id": EventType.BACKPACK_EMPTIED.value,
                    "robot_number": self.robot_id
                })

        if delivery_to_remove_from_dict >= 0:
            del self.deliveries[delivery_to_remove_from_dict]

    def move(self):
        """
        Simple "taxi-like" movement (Manhattan distance):
        - If a target is set, we move towards the target along the X-axis first, then along the Y-axis (or vice versa).
        - No obstacle avoidance.
        """
        if self.current_objective == Objective.WAITING_FOR_FOOD_TO_BE_READY:
            self.pickup_food(self.restaurant_at_which_robot_waits)

        if self.target_x is not None and self.target_y is not None:
            if self.y < self.target_y:
                self.y += 1
            elif self.y > self.target_y:
                self.y -= 1
            elif self.x < self.target_x:
                self.x += 1
            elif self.x > self.target_x:
                self.x -= 1

            # self.x, self.y = self.adjust_to_road(
            #     self.x, self.y, self.road_spacing)

            # Każdy krok zużywa 1 "jednostkę" baterii
            self.current_battery_range -= 1

            # Low battery warning
            if self.current_battery_range <= 0.17 * self.battery_range:
                self.event_queue.enqueue({
                    "id": EventType.LOW_BATTERY_WARNING.value,
                    "robot_number": self.robot_id
                })

            # Sprawdzamy, czy dotarliśmy do celu
            if self.x == self.target_x and self.y == self.target_y:
                # Generate event: Arrived at destination
                if self.current_objective == Objective.PICKING_UP:
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_RESTAURANT.value,
                        "robot_number": self.robot_id,
                        "restaurant": [self.target_x, self.target_y],
                    })
                elif self.current_objective == Objective.GOING_WITH_ORDER:
                    self.give_food([self.x, self.y])
                elif self.target_x == 0 and self.target_y == 0 and self.current_objective == Objective.RETURNING_TO_BASE:
                    self.current_battery_range = self.battery_range
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_BASE.value,
                        "robot_number": self.robot_id,
                    })

                # Clear target
                self.target_x = None
                self.target_y = None
                self.current_objective = Objective.IDLE

        # Battery depleted
        if self.current_battery_range <= 0:
            self.event_queue.enqueue({
                "id": EventType.BATTERY_DEPLETED.value,
                "robot_number": self.robot_id
            })


class Restaurant:
    def __init__(self, x, y, event_queue):
        self.restaurant = [x, y]
        self.order_dict = dict()
        self.event_queue: EventQueue = event_queue

    def give_order(self, order_number):
        del self.order_dict[order_number]

    def start_preparing_order(self, food_details, order_number):
        time = random.randint(1, 15)
        self.order_dict[order_number] = [food_details, time]

    def restaurant_tick(self):
        for order_number, order_details in self.order_dict.items():
            if order_details[1] > 0:
                order_details[1] -= 1

                if order_details[1] == 0: # food ready
                    self.event_queue.enqueue({
                    "id": EventType.FOOD_READY.value,
                    "order_number": order_number,
                    "restaurant": self.restaurant,
                    "food": order_details[0],
                })

class EventQueue:
    def __init__(self):
        self.queue = deque()
        self.num_of_finished_orders = 0
        self.recharged_robots = []

    def enqueue(self, event_dict: dict):
        self.queue.append(event_dict)
        if DEBUG:
            print(f"Enqueuing event: {event_dict}")

    def dequeue(self):
        return self.queue.popleft() if self.queue else None

    def is_empty(self):
        return len(self.queue) == 0

    def process_events(self, robots: list[Robot], restaurants, max_robots, backpack_capacity, next_robot_id, communication: Communication, road_spacing):
        messages_to_send = []

        payload = communication.receive_dict()
        for event in payload:
            event: dict
            self.enqueue(event)

        while not self.is_empty():
            event = self.dequeue()
            event_id = event.get("id", "")

            if event_id == EventType.NEW_ORDER.value:
                messages_to_send.append(
                    event
                )
                if DEBUG:
                    print(f"[EVENT] New order: {event}")

            elif event_id == EventType.SPAWN_COURIER.value:
                id_of_spawned_robot = -1
                if self.recharged_robots:
                    robot_id = self.recharged_robots.pop()
                    for r in robots:
                        if r.robot_id == robot_id:
                            id_of_spawned_robot = robot_id
                            if DEBUG:
                                print(f"[EVENT] Spawning recharged robot with id: {robot_id}")
                else:
                    if len(robots) < max_robots:
                        r = Robot(next_robot_id, 0, 0, event.get(
                            "battery_range", 100), backpack_capacity, self, road_spacing)
                        robots.append(r)
                        id_of_spawned_robot = next_robot_id
                        if DEBUG:
                            print(f"[EVENT] Spawned new courier: ID={next_robot_id}")
                        next_robot_id += 1
                    else:
                        if DEBUG:
                            print("[EVENT] Maximum number of robots reached.")
                        # TODO: raise it to the supervisor

                messages_to_send.append(
                    {
                        "id": EventType.ID_OF_SPAWNED_ROBOT.value,
                        "robot_number": id_of_spawned_robot,
                    }
                )

            elif event_id == EventType.RETURN_TO_BASE.value:
                robot_id = event["robot_number"]
                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(0, 0, Objective.RETURNING_TO_BASE)
                        if DEBUG:
                            print(f"[EVENT] Robot {robot_id} returning to base.")

            elif event_id == EventType.ARRIVED_AT_BASE.value:
                # NOTE Szpak: Supervisor currently does not use this event
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_number"]
                if DEBUG:
                    print(f"[EVENT] Robot {robot_id} arrived at base.")

            elif event_id == EventType.LOW_BATTERY_WARNING.value:
                # NOTE Szpak: Supervisor currently does not use this event
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_number"]
                if DEBUG:
                    print(f"[EVENT] Warning: Robot {robot_id} has low battery.")

            elif event_id == EventType.BATTERY_DEPLETED.value:
                # NOTE Szpak: Supervisor currently does not use this event
                robot_id = event["robot_number"]
                messages_to_send.append(
                    event
                )
                if DEBUG:
                    print(f"[EVENT] Robot {robot_id} battery depleted. Removing from simulation.")
                robots = [r for r in robots if r.robot_id != robot_id]
                # TODO: handle situation when robot is handling order

            elif event_id == EventType.ARRIVED_AT_RESTAURANT.value:
                robot_id = event["robot_number"]
                restaurant = event["restaurant"]
                messages_to_send.append(
                    event
                )
                if DEBUG:
                    print(f"[EVENT] Robot {robot_id} arrived at restaurant {restaurant}.")
                for r in robots:
                    if r.robot_id == robot_id:
                        r.pickup_food(restaurant)
                        if DEBUG:
                            print(f"[EVENT] Robot {robot_id} trying to pick food from restaurant {restaurant}.")

            elif event_id == EventType.ROBOT_PICK_FOOD.value:
                robot_id = event["robot_number"]
                food = event["food"]
                restaurant = event["restaurant"]
                order_number = event["order_number"]

                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(
                            restaurant[0], restaurant[1], Objective.PICKING_UP)
                        r.add_order(restaurant, order_number, food)

                if DEBUG:
                    print(f"[EVENT] Send robot to pick order from restaurant, robot_id = {robot_id}, food = {food}, restaurant = {restaurant}")

            elif event_id == EventType.FOOD_PICKED_UP.value:
                messages_to_send.append(
                    event
                )
                order_number = event["order_number"]
                restaurant = event["restaurant"]
                food_details = event["food"]
                if DEBUG:
                    print(f"[EVENT] Order number {order_number} picked from restaurant {restaurant}. Food: {food_details}")

            elif event_id == EventType.FOOD_READY.value:
                messages_to_send.append(
                    event
                )
                restaurant = event["restaurant"]
                order_number = event["order_number"]
                food_details = event["food"]
                for r in robots:
                    if order_number in r.orders.keys():
                        r.set_order_ready(order_number)

                if DEBUG:
                    print(f"[EVENT] Food ready for pickup at restaurant {restaurant}. Food: {food_details}")

            elif event_id == EventType.DELIVER_FOOD.value:
                robot_id = event["robot_number"]
                address = event["address"]
                food_details = event["food"]
                order_number = event["order_number"]
                for r in robots:
                    if r.robot_id == robot_id:
                        # TODO: Food information is not stored anywhere
                        r.set_target(
                            address[0], address[1], Objective.GOING_WITH_ORDER)
                        r.add_delivery(address, order_number, food_details)
                        if DEBUG:
                            print(f"[EVENT] Robot {robot_id} delivering food to {address}. Food: {food_details}")

            elif event_id == EventType.FOOD_DELIVERED.value:
                messages_to_send.append(
                    event
                )
                self.num_of_finished_orders += 1
                order_number = event["order_number"]
                address = event["address"]
                if DEBUG:
                    print(f"[EVENT] Robot {order_number} delivered food to {address}")

            elif event_id == EventType.BACKPACK_EMPTIED.value:
                messages_to_send.append(
                    event
                )
                robot_id = event["robot_number"]
                if DEBUG:
                    print(f"[EVENT] Robot {robot_id}'s backpack has been emptied.")

            elif event_id == EventType.FOOD_START.value:
                restaurant = event["restaurant"]
                food_details = event["food"]
                order_number = event["order_number"]

                for restaurant_obj in restaurants:
                    if restaurant == restaurant_obj.restaurant:
                        restaurant_obj.start_preparing_order(food_details, order_number)

                if DEBUG:
                    print(f"[EVENT] Restaurant {restaurant} preparing food. Food: {food_details}, {order_number}")

            else:
                if DEBUG:
                    print(f"[EVENT] Unknown event type: {event_id}. Params: {event}")

        communication.send_data(messages_to_send)

        return next_robot_id, self.num_of_finished_orders


def main():
    # 1. Wczytanie konfiguracji
    with open("config.json", 'r', encoding='utf-8') as f:
        config = json.load(f)

    city_size = config["city_size"]  # [width, height], np. [10, 10]
    max_robots = config["max_robots"]  # maks. liczba robotów
    cell_size = config["cell_size"]    # in px
    backpack_capacity = config["backpack_capacity"]
    restaurant_count = config["restaurant_count"]  # liczba restauracji
    road_spacing = 3  # Rozstaw dróg (stały)

    # 2. Inicjalizacja Pygame
    clock = pygame.time.Clock()

    event_queue = EventQueue()

    # 3. Renderer
    renderer = Renderer(city_size, cell_size, restaurant_count)
    restaurants_positions = renderer.get_restaurants()

    restaurants = []
    for x_, y_ in restaurants_positions:
        restaurants.append(Restaurant(x_, y_, event_queue))

    # 4. Communication
    communication = Communication("localhost", int(sys.argv[1]))

    # 5. Lista robotów i zmienna do przydzielania ID
    robots = []
    next_robot_id = 0
    order_number = 0
    number_of_generated_orders = 0

    running = True

    while running:
        # Obsługa zdarzeń Pygame (np. zamknięcie okna)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Generowanie losowych zamówień
        if random.random() < 0.25:  # 5% szansa na tick
            number_of_generated_orders += 1
            address_x = random.randint(0, city_size[0] - 1)
            address_y = random.randint(0, city_size[1] - 1)

            if address_x == 0:
                address_x = 1
            elif (address_x) % 3 == 0:
                address_x -= 1

            if address_y == 0:
                address_y = 1
            elif (address_y) % 3 == 0:
                address_y -= 1

            rest_x, rest_y = random.choice(restaurants_positions)

            food = {"size": random.randint(1, 3)}
            event_queue.enqueue({
                "id": EventType.NEW_ORDER.value,
                "order_number": order_number,
                "food": food,
                "address": [address_x, address_y],
                "restaurant": [rest_x, rest_y],
            })
            order_number += 1

        # Ruch robotów
        for r in robots[:]:
            r: Robot
            if r.battery_range > 0:
                r.move()
            else:
                if DEBUG:
                    print(f"[SIM] Robot {r.robot_id} ma rozładowaną baterię i zostaje usunięty z symulacji.")
                robots.remove(r)

        for restaurant in restaurants:
            restaurant.restaurant_tick()

        # Przetwarzanie zdarzeń
        next_robot_id, finished_orders = event_queue.process_events(
            robots, restaurants, max_robots, backpack_capacity, next_robot_id, communication, road_spacing)

        # Statystyki
        print('Total orders: {:4} | Realized orders: {:4} | Percentage: {:5.2f}%'.format(number_of_generated_orders, finished_orders, 100.0 * float(finished_orders)/number_of_generated_orders if number_of_generated_orders != 0 else 0.0), end='\r')

        # Renderowanie
        renderer.update(robots)
        clock.tick(2)  # 2 FPS – można zmienić w zależności od potrzeb

    pygame.quit()


if __name__ == "__main__":
    main()
