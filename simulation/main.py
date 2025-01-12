import communication
import render
import simulation


if __name__ == "__main__":

    try:
        while True:
            print("Received from supervisor:")
        # The simulation can also send data back here if needed
    except KeyboardInterrupt:
        print("Shutting down Simulation.")
    finally:
        exit(0)
