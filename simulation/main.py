import pygame
import json
import os
import communication
import simulation
import time
import random
from typing import List
from enum import Enum
from collections import deque
from render import Renderer

class Objective(Enum):
    IDLE = 0
    PICKING_UP = 1
    GOING_WITH_ORDER = 2
    RETURNING_TO_BASE = 3

# Event Types
class EventType(Enum):
    NEW_ORDER = "new_order"
    SPAWN_COURIER = "spawn_courier"
    RETURN_TO_BASE = "return_to_base"
    ARRIVED_AT_BASE = "arrived_at_base"
    LOW_BATTERY_WARNING = "low_battery_warning"
    BATTERY_DEPLETED = "battery_depleted"
    ARRIVED_AT_RESTAURANT = "robot_arrived"
    FOOD_PICKED_UP = "food_picked"
    FOOD_READY = "food_ready"
    DELIVER_FOOD = "deliver_food"
    FOOD_DELIVERED = "food_delivered"
    BACKPACK_EMPTIED = "backpack_empty"
    ORDER_FOOD_PREPARATION = "order_food_preparation"


class Robot:
    def __init__(self, robot_id, x, y, battery_range, backpack_capacity, event_queue):
        self.robot_id = robot_id
        self.x = x
        self.y = y
        # zasięg na baterii (np. liczba "kroków")
        self.battery_range = battery_range
        self.current_baterry_range = battery_range
        self.backpack_capacity = backpack_capacity
        self.current_capacity = 0
        self.target_x = None
        self.target_y = None
        self.curent_objective = Objective.IDLE
        self.carrying_food = dict()  # Tu można trzymać informacje o jedzeniu
        self.event_queue: EventQueue = event_queue  # Reference to the event queue

    def set_target(self, tx, ty, type: Objective):
        self.target_x = tx
        self.target_y = ty
        self.curent_objective = type

    def pickup_food(self, food_id, food_capacity):
        """Add food to backpack, simulating pickup of an order from restaurant"""
        if (self.current_capacity + food_capacity) > self.backpack_capacity:
            raise Exception(
                f"Supervisor exceeded max capacity for robot #{self.robot_id}")
        self.current_capacity += food_capacity
        self.carrying_food[food_id] = food_capacity

        # Generate event: Food picked up
        self.event_queue.enqueue({
            "id": EventType.FOOD_PICKED_UP,
            "order_number": "dupa",
            "food": food_id,
            "restaurant": [1, 2],
        })

    def give_food(self, food_id):
        """Remove food from backpack, simulating giving order to customer"""
        removed_capacity = self.carrying_food[food_id]
        self.current_capacity -= removed_capacity
        del self.carrying_food[food_id]

        self.event_queue.enqueue({
            "id": EventType.BACKPACK_EMPTIED,
            "order_number": "dupa",
            "address": [4, 5],
        })

        # Generate event: Backpack emptied
        if self.current_capacity == 0:
            self.event_queue.enqueue({
                "id": EventType.BACKPACK_EMPTIED,
                "robot_number": self.robot_id
            })

    def move(self):
        """
        Simple "taxi-like" movement (Manhattan distance):
        - If a target is set, we move towards the target along the X-axis first, then along the Y-axis (or vice versa).
        - No obstacle avoidance.
        """
        if self.target_x is not None and self.target_y is not None:
            if self.x < self.target_x:
                self.x += 1
            elif self.x > self.target_x:
                self.x -= 1
            elif self.y < self.target_y:
                self.y += 1
            elif self.y > self.target_y:
                self.y -= 1

            # Każdy krok zużywa 1 "jednostkę" baterii
            self.current_baterry_range -= 1

            # Low battery warning
            if self.current_baterry_range <= 0.1 * self.battery_range:
                self.event_queue.enqueue({
                    "id": EventType.LOW_BATTERY_WARNING,
                    "robot_id": self.robot_id
                })

            # Sprawdzamy, czy dotarliśmy do celu
            if self.x == self.target_x and self.y == self.target_y:
                # Generate event: Arrived at destination
                if self.curent_objective == Objective.PICKING_UP:
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_RESTAURANT,
                        "robot_id": self.robot_id,
                        "restaurant_xy": [self.target_x, self.target_y]
                    })
                elif self.curent_objective == Objective.GOING_WITH_ORDER:
                    self.event_queue.enqueue({
                        "id": EventType.FOOD_DELIVERED,
                        "order_number": 1,
                        "address_xy": [self.target_x, self.target_y],
                    })
                elif self.target_x == 0 and self.target_y == 0 and self.curent_objective == Objective.RETURNING_TO_BASE:
                    self.event_queue.enqueue({
                        "id": EventType.ARRIVED_AT_BASE,
                        "robot_id": self.robot_id,
                    })

                # Clear target
                self.target_x = None
                self.target_y = None
                self.curent_objective = Objective.IDLE

        # Battery depleted
        if self.current_baterry_range <= 0:
            self.event_queue.enqueue({
                "id": EventType.BATTERY_DEPLETED,
                "robot_id": self.robot_id
            })


class EventQueue:
    def __init__(self):
        self.queue = deque()

    def enqueue(self, event_dict: dict):
        self.queue.append(event_dict)
        print(f"Added new event of type: {event_dict}")

    def dequeue(self):
        return self.queue.popleft() if self.queue else None

    def is_empty(self):
        return len(self.queue) == 0

    def process_events(self, robots, max_robots, backpack_capacity, next_robot_id):
        """
        Processes all events in the queue and executes their corresponding logic.

        Args:
            robots (list): List of active robots.
            max_robots (int): Maximum allowed robots in the simulation.
            backpack_capacity (int): Default backpack capacity for new robots.
            next_robot_id (int): ID to assign to the next spawned robot.

        Returns:
            int: Updated next_robot_id value.
        """
        while not self.is_empty():
            event = self.dequeue()
            event_id = event.get("id", "")

            if event_id == EventType.NEW_ORDER:
                print(f"[EVENT] New order: {event}")

            elif event_id == EventType.SPAWN_COURIER:
                if len(robots) < max_robots:
                    r = Robot(next_robot_id, 0, 0, event.get(
                        "battery_range", 10), backpack_capacity, self)
                    robots.append(r)
                    print(f"[EVENT] Spawned new courier: ID={next_robot_id}")
                    next_robot_id += 1
                else:
                    print("[EVENT] Maximum number of robots reached.")
                    # TODO: raise it to the supervisor

            elif event_id == EventType.RETURN_TO_BASE:
                robot_id = event["robot_id"]
                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(0, 0, Objective.RETURNING_TO_BASE)
                        print(f"[EVENT] Robot {robot_id} returning to base.")

            elif event_id == EventType.ARRIVED_AT_BASE:
                robot_id = event["robot_id"]
                print(f"[EVENT] Robot {robot_id} arrived at base.")

            elif event_id == EventType.LOW_BATTERY_WARNING:
                robot_id = event["robot_id"]
                print(f"[EVENT] Warning: Robot {robot_id} has low battery.")

            elif event_id == EventType.BATTERY_DEPLETED:
                robot_id = event["robot_id"]
                print(
                    f"[EVENT] Robot {robot_id} battery depleted. Removing from simulation.")
                robots = [r for r in robots if r.robot_id != robot_id]
                # TODO: handle situation when robot is handling order

            elif event_id == EventType.ARRIVED_AT_RESTAURANT:
                robot_id = event["robot_id"]
                restaurant_xy = event["restaurant_xy"]
                self.enqueue({
                    "id": EventType.RETURN_TO_BASE,
                    "robot_id": robot_id
                })
                print(
                    f"[EVENT] Robot {robot_id} arrived at restaurant {restaurant_xy}.")

            elif event_id == EventType.FOOD_PICKED_UP:
                robot_id = event["robot_id"]
                restaurant_xy = event["restaurant_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Robot {robot_id} picked up food from restaurant {restaurant_xy}. Food: {food_details}")

            elif event_id == EventType.FOOD_READY:
                restaurant_xy = event["restaurant_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Food ready for pickup at restaurant {restaurant_xy}. Food: {food_details}")

            elif event_id == EventType.DELIVER_FOOD:
                robot_id = event["robot_id"]
                address_xy = event["address_xy"]
                food_details = event["food"]
                for r in robots:
                    if r.robot_id == robot_id:
                        r.set_target(
                            address_xy[0], address_xy[1], Objective.GOING_WITH_ORDER)
                        print(
                            f"[EVENT] Robot {robot_id} delivering food to {address_xy}. Food: {food_details}")

            elif event_id == EventType.FOOD_DELIVERED:
                robot_id = event["robot_id"]
                address_xy = event["address_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Robot {robot_id} delivered food to {address_xy}. Food: {food_details}")

            elif event_id == EventType.BACKPACK_EMPTIED:
                robot_id = event["robot_id"]
                print(f"[EVENT] Robot {robot_id}'s backpack has been emptied.")

            elif event_id == EventType.ORDER_FOOD_PREPARATION:
                restaurant_xy = event["restaurant_xy"]
                food_details = event["food"]
                print(
                    f"[EVENT] Restaurant {restaurant_xy} preparing food. Food: {food_details}")

            else:
                print(
                    f"[EVENT] Unknown event type: {event_id}. Params: {event}")

        return next_robot_id
    


def load_events_from_file(events_file):
    if not os.path.exists(events_file):
        return []  # brak pliku => brak zdarzeń
    try:
        with open(events_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # data powinno być listą zdarzeń
            return data
    except:
        return []
    

def is_on_road(x, y, road_spacing):
    """
    Sprawdza, czy dana pozycja (x, y) znajduje się na drodze.
    Drogi są zdefiniowane jako kratki, gdzie x % road_spacing == 0 lub y % road_spacing == 0.
    """
    return x % road_spacing == 0 or y % road_spacing == 0


def adjust_to_road(x, y, road_spacing):
    """
    Dostosowuje współrzędne (x, y) do najbliższej kratki drogi.
    """
    if x % road_spacing != 0:
        x = round(x / road_spacing) * road_spacing
    if y % road_spacing != 0:
        y = round(y / road_spacing) * road_spacing
    return x, y


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
    restaurants = renderer.get_restaurants()

    # 4. Lista robotów i zmienna do przydzielania ID
    robots = []
    next_robot_id = 1

    running = True

    while running:
        # Obsługa zdarzeń Pygame (np. zamknięcie okna)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Dodanie nowego robota, jeśli jest miejsce
        if len(robots) < max_robots:
            r = Robot(next_robot_id, 0, 0, 30, backpack_capacity, event_queue)
            
            # Wybierz losową restaurację i dostosuj ją do drogi
            rest_x, rest_y = random.choice(restaurants)
            rest_x, rest_y = adjust_to_road(rest_x, rest_y, road_spacing)
            
            r.set_target(rest_x, rest_y, Objective.PICKING_UP)
            robots.append(r)
            print(f"[SIM] Spawn nowego robota o ID={next_robot_id}")
            next_robot_id += 1

        # Generowanie losowych zamówień
        if random.random() < 0.1:  # 10% szansa na tick
            address_x = random.randint(0, city_size[0] - 1)
            address_y = random.randint(0, city_size[1] - 1)

            # Dostosuj adres do drogi
            address_x, address_y = adjust_to_road(address_x, address_y, road_spacing)

            rest_x, rest_y = random.choice(restaurants)
            rest_x, rest_y = adjust_to_road(rest_x, rest_y, road_spacing)

            food = {"size": random.randint(1, 3)}
            event_queue.enqueue({
                "id": EventType.NEW_ORDER,
                "address": [address_x, address_y],
                "restaurant": [rest_x, rest_y],
                "food": food
            })

        # Ruch robotów
        for r in robots[:]:
            if r.battery_range > 0:
                r.move()
            else:
                print(f"[SIM] Robot {r.robot_id} ma rozładowaną baterię i zostaje usunięty z symulacji.")
                robots.remove(r)

        # Przetwarzanie zdarzeń
        next_robot_id = event_queue.process_events(robots, max_robots, backpack_capacity, next_robot_id)

        # Renderowanie
        renderer.update(robots)
        clock.tick(2)  # 2 FPS – można zmienić w zależności od potrzeb

    pygame.quit()


if __name__ == "__main__":
    main()
