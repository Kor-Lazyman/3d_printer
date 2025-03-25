import salabim as sim
from config_SimPy import *


class Worker:
    """
    Worker class to represent a worker in the manufacturing process
    One type of processor in the simulation

    Attributes:
        type_processor (str): Type of processor (Worker)
        id_worker (int): Worker ID
        name_worker (str): Worker name
        available_status (bool): Worker availability status
        working_job (Job): Job currently being processed
        processing_time (int): Time taken to process a job
        busy_time (int): Total time spent processing jobs
        last_status_change (int): Time of last status change
    """

    def __init__(self, id_worker, name_worker, processing_time):
        self.type_processor = "Worker"
        self.id_worker = id_worker
        self.name_worker = name_worker
        self.available_status = True
        self.working_job = None
        self.processing_time = processing_time
        self.busy_time = 0
        self.last_status_change = 0


class Machine:
    """
    Machine class to represent a machine in the manufacturing process
    One type of processor in the simulation

    Attributes:
        type_processor (str): Type of processor (Machine)
        id_machine (int): Machine ID
        name_process (str): Process name
        name_machine (str): Machine name
        available_status (bool): Machine availability status
        list_working_jobs (list): List of jobs currently being processed
        capacity_jobs (int): Maximum number of jobs that can be processed simultaneously
        processing_time (int): Time taken to process a job
        busy_time (int): Total time spent processing jobs
        last_status_change (int): Time of last status change
        allows_job_addition_during_processing (bool): Flag to allow job addition during processing
    """

    def __init__(self, id_machine, name_process, name_machine, processing_time, capacity_jobs=1):
        self.type_processor = "Machine"
        self.id_machine = id_machine
        self.name_process = name_process
        self.name_machine = name_machine
        self.available_status = True
        self.list_working_jobs = []
        self.capacity_jobs = capacity_jobs
        self.processing_time = processing_time
        self.busy_time = 0
        self.last_status_change = 0
        self.allows_job_addition_during_processing = False


import salabim as sim

class ProcessorResource(sim.Resource):
    """
    Integrated processor (Machine, Worker) resource management class in Salabim.

    Attributes:
        processor_type (str): Type of processor (Machine/Worker)
        id (int): Processor ID
        name (str): Processor name
        allows_job_addition_during_processing (bool): Flag to allow job addition during processing
        current_jobs (list): List of jobs currently being processed (Machines)
        current_job (Job): Job currently being processed (Worker)
        processing_time (int): Time taken to process a job
    """

    def __init__(self, env, processor,**kwargs):
        super().__init__(**kwargs)
        self.env = env  # Salabim 환경 객체

        # Check processor type and set properties
        self.processor_type = getattr(processor, 'type_processor', 'Unknown')
        self.num_capacity =  getattr(processor, 'capacity_jobs', 1)
        # Set capacity - Machine uses capacity_jobs, Worker always 1
        if self.processor_type == "Machine":
            self._capacity = getattr(processor, 'capacity_jobs', 1)
            self.id = getattr(processor, 'id_machine', 0)
            self._name = getattr(processor, 'name_machine', 'Machine')
            self.allows_job_addition_during_processing = getattr(
                processor, 'allows_job_addition_during_processing', True)
            self.current_jobs = []

        elif self.processor_type == "Worker":
            self._capacity = 1  # Worker always processes one job at a time
            self.id = getattr(processor, 'id_worker', 0)
            self._name = getattr(processor, 'name_worker', 'Worker')
            self.allows_job_addition_during_processing = False
            self.current_job = None
            self.current_jobs = []  # Added for consistency
        print(f"name:{self.name()},capa{self._capacity}")
        self.processor = processor
        self.processing_time = getattr(processor, 'processing_time', 10)
        # Salabim Resource (대기열 포함)

        # Flag to prevent further resource allocation after processing starts
        self.processing_started = False

    def request(self):
        """
        Override resource request - Check if addition during processing is allowed.
        """
        # If already processing and addition not allowed, return an infinite-wait event
        '''
        if self.processing_started and not self.allows_job_addition_during_processing:
            dummy_event = self.env.event()
            dummy_event.succeed()  # 이벤트 완료 상태로 설정하여 대기하도록 함
            return dummy_event
        '''
        # Set flag when job is first assigned to resource
        if not self.processing_started and self.claimers().length() == 0:
            self.processing_started = True
            return True
        else:
            return False
        # Process basic request
        

    def release(self):
        """
        Override resource release - Handle job completion.
        """
        
        super().release()
        self.num_capacity +=1
        '''
        # Reset processing flag when all jobs are complete
        if self.claimers().length() == 0:
            self.processing_started = False
            if self.processor_type == "Machine":
                self.current_jobs = []
            else:  # Worker
                self.current_job = None
                self.current_jobs = []
        '''
    @property
    def is_available(self):
        """Check if processor is available"""
        # Not available if processing and additions not allowed
        if self.processing_started and not self.allows_job_addition_during_processing:
            return False

        # Available if capacity has room
        return self.available_quantity() > 0

    def start_job(self, job):
        """Process job start"""
        if self.processor_type == "Machine":
            # Add job to Machine
            self.current_jobs.append(job)
        else:  # Worker
            # Set Worker's current job
            self.current_job = job
            self.current_jobs = [job]  # Consistency

        # Set workstation info in job
        if self.processor_type == "Machine":
            job.workstation["Machine"] = self.id
        else:  # Worker
            job.workstation["Worker"] = self.id

    def get_jobs(self):
        """Return list of currently processing jobs"""
        if self.processor_type == "Machine":
            return self.current_jobs
        else:  # Worker
            return [self.current_job] if self.current_job else []

    def finish_jobs(self):
        """Process job completion"""
        jobs = self.get_jobs()

        if self.processor_type == "Machine":
            self.current_jobs = []
        else:  # Worker
            self.current_job = None
            self.current_jobs = []

        return jobs
