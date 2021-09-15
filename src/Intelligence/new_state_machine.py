"""TODO: Add a docstring!
IDK wtf this is Jimmy but it's getting renamed to new_state_machine for now -IAR
"""

import docker

import client


CLIENT = docker.from_env()


def DestroyAllContainers():
    """TODO: Add a docstring!
    """
    containers_list = CLIENT.containers.list(all=True)
    for cont in containers_list:
        cont.remove(force=True)


class SimpleDevice(object):
    """
    A simple state machine that mimics the functionality of a device from a
    high level.
    """

    def __init__(self):
        """ Initialize the components. """
        # Start with a default state.
        # CLIENT.containers.run(name="minisub", command=None, image="ubuntu", detach=True)
        self.state = LockedState()
        self.container = True

    def on_event(self, event):
        """
        This is the bread and butter of the state machine. Incoming events are
        delegated to the given states which then handle the event. The result is
        then assigned as the new state.
        """
        # The next state will be the result of the on_event function.
        self.state = self.state.on_event(event)

    def tasks(self, task):
        """TODO: Add a docstring!
        """
        # Delegate Tasks based on state
        self.state = self.state.tasks(task)


def Interpret():
    """TODO: Add a docstring!
        """
    info = client.response.message
    print("hello")
    print(info)


class State(object):
    """
    We define a state object which provides some utility functions for the
    individual states within the state machine.
    """

    def __init__(self):
        print('Processing current state:', str(self))

    def tasks(self):
        """
        Handles event Based on Current State
        """
        pass

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
    """TODO: Add a docstring!
    """
    def __init__(self):
        """ Initialize the components. """
        containers_list = CLIENT.containers.list(all=True)
        if not containers_list:
            self.container = False
        else:
            self.container = True
        self.tasks()

    """
    The state which indicates that there are limited device capabilities.
    """

    def tasks(self):
        """TODO: Add a docstring!
        """
        print("Deleting all Docker Containers...")
        if not self.container:
            CLIENT.containers.run(name="minisub", command=None, image="ubuntu", detach=True)
            self.container = True
        else:
            containers_list = CLIENT.containers.list(all=True)
            for cont in containers_list:
                cont.remove(force=True)
                self.container = False
                CLIENT.containers.run(name="minisub", command=None, image="ubuntu", detach=True)
                self.container = True
        print("All Docker containers Deleted")

    def on_event(self, event):
        """TODO: Add a docstring!
        """
        if event == 'Normal_Operation':
            return UnlockedState()
        if event == 'Caution_Operation':
            return CautionState()

        return self


class UnlockedState(State):
    """TODO: Add a docstring!
    """
    def __init__(self):
        """ Initialize the components. """
        containers_list = CLIENT.containers.list(all=True)
        if not containers_list:
            self.container = False
        else:
            self.container = True
        self.tasks()

    def tasks(self):
        """TODO: Add a docstring!
        """
        print("Building {} Container".format(self))
        if not self.container:
            CLIENT.containers.run(name="minisub", command=None, image="ubuntu", detach=True)
            self.container = True
        return

    """
    The state which indicates that there are no limitations on device
    capabilities.
    """

    def on_event(self, event):
        """TODO: Add a docstring!
        """
        if event == 'Error_Operation':
            return LockedState()
        if event == 'Caution_Operation':
            return CautionState()
        return self


class CautionState(State):
    """TODO: Add a docstring!
    """
    def __init__(self):
        """ Initialize the components. """
        containers_list = CLIENT.containers.list(all=True)
        if not containers_list:
            self.container = False
        else:
            self.container = True
        self.tasks()

    def tasks(self):
        """TODO: Add a docstring!
        """
        containers_list = CLIENT.containers.list(all=True)
        for cont in containers_list:
            cont.remove(force=True)
            self.container = False
        CLIENT.containers.run(name="minisub", command=None, image="ubuntu", detach=True)
        self.container = True
        minisub = CLIENT.containers.get("minisub")
        minisub.restart(timeout=2)
        return

    """
    The state which indicates that there is a minor limitation on device
    capabilities
    """

    def on_event(self, event):
        """TODO: Add a docstring!
        """
        if event == "Error_Operation":
            return LockedState()
        if event == 'Normal_Operation':
            return UnlockedState()
        return self


if __name__ == '__main__':
    Interpret()
# End of our states.
