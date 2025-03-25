#import simpy
import salabim as sim

class Job(sim.Component):
    """
    Job class to represent a job in the manufacturing process

    Attributes:
        id_job (int): Unique job identifier
        workstation (dict): Current workstation assignment
        list_items (list): List of items in the job
        time_processing_start (float): Time when processing started
        time_processing_end (float): Time when processing ended
        time_waiting_start (float): Time when waiting started
        time_waiting_end (float): Time when waiting ended
        is_reprocess (bool): Flag for reprocessed jobs
        processing_history (list): List of processing history
    """

    def __init__(self, id_job, list_items, **kwargs):
        super().__init__(**kwargs)
        self.id_job = id_job
        self.workstation = {"Process": None, "Machine": None, "Worker": None}
        self.list_items = list_items
        self.time_processing_start = None
        self.time_processing_end = None
        self.time_waiting_start = None
        self.time_waiting_end = None
        self.is_reprocess = False  # Flag for reprocessed jobs

        # Add processing history to track jobs across all processes
        self.processing_history = []  # Will store each process step details


class JobStore(sim.Store):
    """
    Job queue management class that inherits SimPy Store

    Attributes:
        env (simpy.Environment): Simulation environment
        name (str): Name of the JobStore
        queue_length_history (list): Queue length
    """

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self.queue_length_history = []  # Track queue length history

    def add(self, item):
        #print(self.store)
        """Add Job to Store (override)"""
        result = super().add(item)
        # Record queue length
        self.queue_length_history.append((self.env.now(), self._length))
        return result

    def from_store(self):
        """Get Job from queue (override)"""
        result = super().pop()
        # Record queue length when getting result
        # Use event chain instead of callback
        def process_get(env, result):
            self.queue_length_history.append((self.env.now(), self._length))
        process_get(self.env, result)
        return result

    @property
    def is_empty(self):
        """Check if queue is empty"""
        return self._length == 0

    @property
    def size(self):
        """Current queue size"""
        return self._length
