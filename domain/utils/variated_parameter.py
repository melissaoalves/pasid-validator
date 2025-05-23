from enum import Enum

class VariatedParameter(Enum):
    SERVICES = "Services"
    AR = "AR"

    @staticmethod
    def from_value(value: str) -> "VariatedParameter":
        for param in VariatedParameter:
            if param.value.lower() == value.lower():
                return param
        raise ValueError(f"Invalid VariatedParameter value: {value}")
