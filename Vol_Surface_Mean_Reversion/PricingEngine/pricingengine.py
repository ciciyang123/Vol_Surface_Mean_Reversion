from abc import abstractmethod
from enum import Enum


class Arguments:
    @abstractmethod
    def validate(self): pass


class Results:
    @abstractmethod
    def reset(self): pass


# interface for pricing engine
class PricingEngine(Exception):
    @abstractmethod
    def get_arguments(self) -> Arguments: pass

    @abstractmethod
    def get_result(self) -> Results: pass

    @abstractmethod
    def reset(self) -> None: pass

    @abstractmethod
    def calculate(self) -> None: pass


class PricingEngineError(Exception):
    class State(Enum):
        IllegalNegativeParameter = -1
        IllegalNonPositiveParameter = -2
        InvalidOptionType = -3
        NonInitialArguments = -4
        ImproperExerciseType = -5
        ImproperPayoffType = -6
        UnConformProcess = -7
        UnSupportArgumentType = -8
        NegativeVolatility = -9

    def __init__(self, state: State, msg: str = ""):
        self.state_ = state
        self.msg_ = msg

    @abstractmethod
    def error_state(self) -> State:
        return self.state_
