from copy import deepcopy
import logging


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


############################### Leaf Nodes ##################################
class Check(Node):
    def __init__(self, check_function):
        self.check_function = check_function

    @log_execution
    def execute(self, state):
        return self.check_function(state)

    def __str__(self):
        return self.__class__.__name__ + ': ' + self.check_function.__name__


class PushToStack(Node):
    def __init__(self, blackboard : dict, stack_name, item_key):
        self.blackboard = blackboard
        assert self.blackboard, "Blackboard is None in PushToStack Constructor"
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
        self.blackboard[self.stack_key].append(item)


class PopFromStack(Node):
    def __init__(self, blackboard : dict, stack_name, item_key):
        self.blackboard = blackboard
        assert self.blackboard, "Blackboard is None in PushToStack Constructor"
        self.stack_key = stack_name
        self.item_key = item_key
    
    @log_execution
    def execute(self, state):
        stack = self.blackboard.get(self.stack_key, None)
        assert isinstance(stack, list), f"Item with key stack_key in blackboard is not a list: {stack}"
        if not isinstance(stack, list) or len(stack) == 0:
            return False
        self.blackboard[self.item_key] = stack.pop()


class SetVar(Node):
    def __init__(self, var_key, value_function):
        self.var_key = var_key
        self.value_function = value_function

    @log_execution
    def execute(self, state):
        state[self.var_key] = self.value_function(state)
        return True


class Action(Node):
    def __init__(self, action_function):
        self.action_function = action_function

    @log_execution
    def execute(self, state):
        return self.action_function(state)

    def __str__(self):
        return self.__class__.__name__ + ': ' + self.action_function.__name__
