import os
import contextlib
import torch
import intel_extension_for_pytorch as ipex
from modules import shared
from .diffusers import ipex_diffusers
from .hijacks import ipex_hijacks

#ControlNet depth_leres++
class DummyDataParallel(torch.nn.Module):
    def __new__(cls, module, device_ids=None, output_device=None, dim=0):
        if type(device_ids) is list and len(device_ids) > 1:
            shared.log.warning("IPEX backend doesn't support DataParallel on multiple XPU devices")
        return module.to(shared.device)

def return_null_context(*args, **kwargs):
    return contextlib.nullcontext()

def ipex_init():
    #Replace cuda with xpu:
    torch.cuda.current_device = torch.xpu.current_device
    torch.cuda.current_stream = torch.xpu.current_stream
    torch.cuda.device = torch.xpu.device
    torch.cuda.device_count = torch.xpu.device_count
    torch.cuda.device_of = torch.xpu.device_of
    torch.cuda.getDeviceIdListForCard = torch.xpu.getDeviceIdListForCard
    torch.cuda.get_device_name = torch.xpu.get_device_name
    torch.cuda.get_device_properties = torch.xpu.get_device_properties
    torch.cuda.init = torch.xpu.init
    torch.cuda.is_available = torch.xpu.is_available
    torch.cuda.is_initialized = torch.xpu.is_initialized
    torch.cuda.set_device = torch.xpu.set_device
    torch.cuda.stream = torch.xpu.stream
    torch.cuda.synchronize = torch.xpu.synchronize
    torch.cuda.Event = torch.xpu.Event
    torch.cuda.Stream = torch.xpu.Stream
    torch.cuda.FloatTensor = torch.xpu.FloatTensor
    torch.Tensor.cuda = torch.Tensor.xpu
    torch.Tensor.is_cuda = torch.Tensor.is_xpu

    #Memory:
    torch.cuda.empty_cache = torch.xpu.empty_cache
    torch.cuda.memory_stats = torch.xpu.memory_stats
    torch.cuda.memory_summary = torch.xpu.memory_summary
    torch.cuda.memory_snapshot = torch.xpu.memory_snapshot
    torch.cuda.memory_allocated = torch.xpu.memory_allocated
    torch.cuda.max_memory_allocated = torch.xpu.max_memory_allocated
    torch.cuda.memory_reserved = torch.xpu.memory_reserved
    torch.cuda.max_memory_reserved = torch.xpu.max_memory_reserved
    torch.cuda.reset_peak_memory_stats = torch.xpu.reset_peak_memory_stats
    torch.cuda.memory_stats_as_nested_dict = torch.xpu.memory_stats_as_nested_dict
    torch.cuda.reset_accumulated_memory_stats = torch.xpu.reset_accumulated_memory_stats

    #RNG:
    torch.cuda.get_rng_state = torch.xpu.get_rng_state
    torch.cuda.get_rng_state_all = torch.xpu.get_rng_state_all
    torch.cuda.set_rng_state = torch.xpu.set_rng_state
    torch.cuda.set_rng_state_all = torch.xpu.set_rng_state_all
    torch.cuda.manual_seed = torch.xpu.manual_seed
    torch.cuda.manual_seed_all = torch.xpu.manual_seed_all
    torch.cuda.seed = torch.xpu.seed
    torch.cuda.seed_all = torch.xpu.seed_all
    torch.cuda.initial_seed = torch.xpu.initial_seed

    #Training:
    try:
        torch.cuda.amp.GradScaler = torch.xpu.amp.GradScaler
    except Exception:
        torch.cuda.amp.GradScaler = ipex.cpu.autocast._grad_scaler.GradScaler

    #C
    torch._C._cuda_getCurrentRawStream = ipex._C._getCurrentStream
    ipex._C._DeviceProperties.major = 2023
    ipex._C._DeviceProperties.minor = 2

    #Fix functions with ipex:
    torch.cuda.mem_get_info = lambda device=None: [(torch.xpu.get_device_properties(device).total_memory - torch.xpu.memory_allocated(device)), torch.xpu.get_device_properties(device).total_memory]
    torch._utils._get_available_device_type = lambda: "xpu" # pylint: disable=protected-access
    torch.xpu.empty_cache = torch.xpu.empty_cache if "WSL2" not in os.popen("uname -a").read() else lambda: None
    torch.cuda.get_device_properties.major = 2023
    torch.cuda.get_device_properties.minor = 2
    torch.backends.cuda.sdp_kernel = return_null_context
    torch.nn.DataParallel = DummyDataParallel
    torch.cuda.ipc_collect = lambda: None
    torch.cuda.utilization = lambda: 0

    ipex_hijacks()
    ipex_diffusers()
    try:
        from .openvino import openvino_fx
    except Exception:
        pass
