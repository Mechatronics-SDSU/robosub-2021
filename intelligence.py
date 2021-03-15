# simple_device.py
import sys,time


class SimpleDevice(object):
    """
    A simple state machine that mimics the functionality of a device from a 
    high level.
    """
    def __init__(self):
        """ Initialize the components. """
        # Start with a default state.
        self.state = LockedState()


    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """
        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)

    def tasks(self, task):
        #Delegate Tasks based on state
        self.state = self.state.tasks(task)


class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """


    def __init__(self):
        print('Processing current state:', str(self))


    def tasks(self, task):
        return


    def on_event(self, event):
        """
        Handle events that are delegated to this State.
        """
        pass


    def __repr__(self):
        """
        Leverages the __str__ method to describe the State.
        """
        return self.__str__()


    def __str__(self):
        """
        Returns the name of the State.
        """
        return self.__class__.__name__


class LockedState(State):

    def tasks(self, task):
        return
    """
    The state which indicates that there are limited device capabilities.
    """

    def on_event(self, event):
        if event == 'Normal_Operation':
            return UnlockedState()
        if event == 'Caution_Operation':
            return CautionState()

        return self


class UnlockedState(State):
    def tasks(self, task):
        return
    """
    The state which indicates that there are no limitations on device
    capabilities.
    """
    def on_event(self, event):
        if event == 'Error_Operation':
            return LockedState()
        if event == 'Caution_Operation':
            return CautionState()
        return self


class CautionState(State):

    def tasks(self, task):
        return
    """
    The state which indicates that there is a minor limitation on device
    capabilities
    """
    def on_event(self, event):
        if event == "Error_Operation":
            return LockedState()
        if event == 'Normal_Operation':
            return UnlockedState()
        return self
# End of our states.


print("Initializing the state machine ...")
print("-"*70)
dev = SimpleDevice()
print("System Check is Good ...")
print("Moving on to Normal Operation")
# ----------------------------------------
dev.on_event("Normal_Operation")
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
# ----------------------------------------
print("Emulating an Error Occurrring ...")
dev.on_event("Error_Operation")
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
# ----------------------------------------
print("System Recovered ...")
print("Doing System Checkup ...")
dev.on_event("Caution_Operation")
print("Current State of the State Machine\n")
print(dev.state, "\n")
time.sleep(3)
print("System Checkup Results in: 0 Failures")
print("moving on to normal operation")
dev.on_event("Normal_Operation")
print("Current State of the State Machine")
print(dev.state)
time.sleep(3)
print("End Simulation")
sys.exit(0)
