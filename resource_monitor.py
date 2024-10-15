# resource_monitor.py

import psutil

class ResourceMonitor:
    def __init__(self):
        self.cpu_usage_history = []
        self.memory_usage_history = []
        self.disk_usage_history = []
        self.net_sent_history = []
        self.net_recv_history = []

    def get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)

    def get_memory_usage(self):
        return psutil.virtual_memory().percent

    def get_disk_usage(self):
        return psutil.disk_usage('/').percent

    def get_network_usage(self):
        net_info = psutil.net_io_counters()
        return net_info.bytes_sent / (1024 ** 2), net_info.bytes_recv / (1024 ** 2)

    def update_usage_data(self):
        """Updates historical data for CPU, Memory, Disk, and Network."""
        self.cpu_usage_history.append(self.get_cpu_usage())
        self.memory_usage_history.append(self.get_memory_usage())
        self.disk_usage_history.append(self.get_disk_usage())

        sent, recv = self.get_network_usage()
        self.net_sent_history.append(sent)
        self.net_recv_history.append(recv)

        # Limit the data to 60 points to keep graphs clean and manageable
        if len(self.cpu_usage_history) > 60:
            self.cpu_usage_history.pop(0)
            self.memory_usage_history.pop(0)
            self.disk_usage_history.pop(0)
            self.net_sent_history.pop(0)
            self.net_recv_history.pop(0)

        return {
            'cpu': self.cpu_usage_history,
            'memory': self.memory_usage_history,
            'disk': self.disk_usage_history,
            'network': {'sent': self.net_sent_history, 'recv': self.net_recv_history}
        }
