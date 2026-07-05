# Active runtime exports.
from .gateway_runtime import AegisGatewayKernel, AegisGatewayRuntime
from .amygdala_policy import GLOBAL_KERNEL_PROMPT, global_amygdala
from .module_inventory import get_module_inventory, get_module_lifecycle

__all__ = [
    "AegisGatewayRuntime",
    "AegisGatewayKernel",
    "global_amygdala",
    "GLOBAL_KERNEL_PROMPT",
    "get_module_inventory",
    "get_module_lifecycle",
]
