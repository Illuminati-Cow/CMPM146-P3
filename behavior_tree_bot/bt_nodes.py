from copy import deepcopy
from typing import Callable, Optional, Any, Dict
import logging
from planet_wars import PlanetWars


def log_execution(fn):
    def logged_fn(self, state):
        logging.debug('Executing:' + str(self))
        result = fn(self, state)
        logging.debug('Result: ' + str(self) + ' -> ' + ('Success' if result else 'Failure'))
        return result
    return logged_fn


############################### Base Classes ##################################
class Node:
    def __init__(self):
        raise NotImplementedError

    def execute(self, state):
        raise NotImplementedError

    def copy(self):
        return deepcopy(self)


class Composite(Node):
    def __init__(self, child_nodes=[], name=None):
        self.child_nodes = child_nodes
        self.name = name

    def execute(self, state):
        raise NotImplementedError

    def __str__(self):
        return self.__class__.__name__ + ': ' + self.name if self.name else ''

    def tree_to_string(self, indent=0):
        string = '| ' * indent + str(self) + '\n'
        for child in self.child_nodes:
            if hasattr(child, 'tree_to_string'):
                string += child.tree_to_string(indent + 1)
            else:
                string += '| ' * (indent + 1) + str(child) + '\n'
        return string


class Decorator(Node):
    def __init__(self, child_node):
        self.child_node = child_node

    def execute(self, state):
        raise NotImplementedError

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node)

############################### Composite Nodes ##################################
class Selector(Composite):
    @log_execution
    def execute(self, state):
        for child_node in self.child_nodes:
            success = child_node.execute(state)
            if success:
                return True
        else:  # for loop completed without success; return failure
            return False


class Sequence(Composite):
    @log_execution
    def execute(self, state):
        for child_node in self.child_nodes:
            continue_execution = child_node.execute(state)
            if not continue_execution:
                return False
        else:  # for loop completed without failure; return success
            return True

############################### Decorator Nodes ##################################
class Inverter(Decorator):
    def __init__(self, child_node):
        self.child_node = child_node

    @log_execution
    def execute(self, state):
        result = self.child_node.execute(state)
        return not result

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node)


class UntilFailure(Decorator):
    def __init__(self, child_node):
        self.child_node = child_node

    @log_execution
    def execute(self, state):
        while True:
            continuing_execution = self.child_node.execute(state)
            if not continuing_execution:
                return False

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node)
    

class DoNTimes(Decorator):
    def __init__(self, child_node, n):
        self.child_node = child_node
        self.n = n
        self.counter = 0

    @log_execution
    def execute(self, state):
        while self.counter < self.n:
            result = self.child_node.execute(state)
            self.counter += 1
            if not result:
                return False
        return True

    def reset(self):
        self.counter = 0

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node) + ' (n=' + str(self.n) + ')'
    

class Succeeder(Decorator):
    def __init__(self, child_node):
        self.child_node = child_node

    @log_execution
    def execute(self, state):
        self.child_node.execute(state)
        return True

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node)


class Failer(Decorator):
    def __init__(self, child_node):
        self.child_node = child_node

    @log_execution
    def execute(self, state):
        self.child_node.execute(state)
        return False

    def __str__(self):
        return self.__class__.__name__ + ': ' + str(self.child_node)
    
############################### Leaf Nodes ##################################
class Check(Node):
    def __init__(self, check_function: Callable[[PlanetWars, Optional[dict]], bool], blackboard=None):
        self.check_function = check_function
        self.blackboard = blackboard

    @log_execution
    def execute(self, state):
        try:
            return self.check_function(state)
        except TypeError:
            try:
                return self.check_function(state, self.blackboard)
            except Exception as e:
                logging.log(logging.ERROR, "check function has invalid signature: ", e)
                return False
        except Exception as e:
            logging.log(logging.ERROR, "check function has unknown exception", e)
            raise e
            return False
            

    def __str__(self):
        return self.__class__.__name__ + ': ' + self.check_function.__name__


class PushToStack(Node):
    def __init__(self, blackboard : dict, stack_name, item_key):
        self.blackboard = blackboard
        assert self.blackboard is not None, "Blackboard is None in PushToStack Constructor"
        self.stack_key = stack_name
        self.item_key = item_key

    @log_execution
    def execute(self, state):
        item = self.blackboard.get(self.item_key, None)
        assert item is not None, "Item with key item_key in blackboard is not found"
        if not item:
            return False
        if not self.stack_key in self.blackboard:
            self.blackboard[self.stack_key] = []
        logging.info(f"Pushed item to stack {self.stack_key}: {item}")
        self.blackboard[self.stack_key].append(item)
        return True


class PopFromStack(Node):
    def __init__(self, blackboard : dict, stack_name, item_key):
        self.blackboard = blackboard
        assert self.blackboard is not None, "Blackboard is None in PushToStack Constructor"
        self.stack_key = stack_name
        self.item_key = item_key
    
    @log_execution
    def execute(self, state):
        stack = self.blackboard.get(self.stack_key, None)
        assert isinstance(stack, list), f"Item with key stack_key in blackboard is not a list: {stack}"
        if not isinstance(stack, list) or len(stack) == 0:
            return False
        logging.info(f"Popped from stack {self.stack_key} value: {stack[-1]}")
        self.blackboard[self.item_key] = stack.pop()
        return True


class SetVar(Node):
    def __init__(self, blackboard : dict, var_key, value_function: callable):
        self.var_key = var_key
        self.value_function = value_function
        self.blackboard = blackboard

    @log_execution
    def execute(self, state):
        self.blackboard[self.var_key] = self.value_function(state)
        logging.info(f"Setting Variable {self.var_key} with value: {self.blackboard[self.var_key]}")
        return True
    

class IsVarNull(Node):
    def __init__(self, blackboard : dict, var_key):
        self.var_key = var_key
        self.blackboard = blackboard

    @log_execution
    def execute(self, state) -> bool:
        return self.blackboard.get(self.var_key, None) is None


class Action(Node):
    def __init__(self, action_function):
        self.action_function = action_function

    @log_execution
    def execute(self, state):
        return self.action_function(state)

    def __str__(self):
        return self.__class__.__name__ + ': ' + self.action_function.__name__
