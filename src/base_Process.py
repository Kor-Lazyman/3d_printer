from base_Job import JobStore
from base_Processor import ProcessorResource
import salabim as sim
class Process(sim.Component):
    def __init__(self, triger, processor_resource, jobs, **kwargs):
        super().__init__(**kwargs)
        self.logger = triger.logger
        self._name = triger.name()
        self.triger = triger
        # Next process
        self.processor_resource = processor_resource
        self.jobs = jobs
        self.next_process = triger.next_process
        
    def process(self):
        # Request processor resource
        self.request(self.processor_resource)
        for job in self.jobs:
            job.time_waiting_end = self.env.now()

            # Register job with processor
            self.processor_resource.start_job(job)

            if self.logger:
                self.logger.log_event(
                    "Processing", f"Assigning job {job.id_job} to {self.processor_resource.name()}")

            # Record job start time
            job.time_processing_start = self.env.now()

            # Record job processing history
            process_step = self.create_process_step(job, self.processor_resource)
            if not hasattr(job, 'processing_history'):
                job.processing_history = []
            job.processing_history.append(process_step)
        # Calculate and wait for processing time
        processing_time = self.processor_resource.processing_time
        self.hold(processing_time)

        # Special processing (if needed)
        if hasattr(self, 'apply_special_processing'):
            self.apply_special_processing(self.processor_resource.processor, self.jobs)

        # Process job completion
        for job in self.jobs:
            job.time_processing_end = self.env.now()

            # Update job history
            for step in job.processing_history:
                if step['process'] == self.name() and step['end_time'] is None:
                    step['end_time'] = self.env.now()
                    step['duration'] = self.env.now() - step['start_time']

            # Track completed jobs
            self.triger.completed_jobs.append(job)

            # Log record
            if self.logger:
                self.logger.log_event(
                    "Processing", f"Completed processing job {job.id_job} on {self.processor_resource.name()}")

            # Send job to next process
            self.send_job_to_next(job)

        # Release resources
        self.release_resources(self.processor_resource)

    def release_resources(self, processor_resource):
        """
        Release processor resources and process job completion

        Args:
            processor_resource (ProcessorResource): Processor resource (Machine, Worker)
            request (simpy.Request): Resource request 

        """
        # Release processor resource
        if self.name() == "Proc_Wash":
            print("release_time",self.env.now(),processor_resource._claimed_quantity,processor_resource.claimers()._length)
        processor_resource.release()
        processor_resource.finish_jobs()
        if self.name() == "Proc_Wash":
            print("release_time",self.env.now(),processor_resource._claimed_quantity,processor_resource.claimers()._length)

        if self.logger:
            self.logger.log_event(
                "Resource", f"Released {processor_resource.name(), self.jobs} in {self.name()}")

        # Trigger resource release event (for event-based approach)
        self.triger.process()

        
    def create_process_step(self, job, processor_resource):
        """Create process step for job history"""
        return {
            'process': self.name(),
            'resource_type': processor_resource.processor_type,
            'resource_id': processor_resource.id,
            'resource_name': processor_resource.name(),
            'start_time': job.time_processing_start,
            'end_time': None,
            'duration': None
        }

    def send_job_to_next(self, job):
        """Send job to next process"""
        if self.next_process:
            if self.logger:
                self.logger.log_event(
                    "Process Flow", f"Moving job {job.id_job} from {self.name()} to {self.next_process.name()}")
            # Add job to next process queue
            self.next_process.add_to_queue(job)
            return True
        else:
            # Final process or no next process set
            if self.logger:
                self.logger.log_event(
                    "Process Flow", f"Job {job.id_job} completed at {self.name()} (final process)")
            return False

class Job_Trigger(sim.Component):
    def __init__(self, name, env, logger=None, **kwargs):
        super().__init__(**kwargs)
        self._name = name
        self.env = env
        self.logger = logger
        self.list_processors = []  # Processor list
        # Implement queue with JobStore (Inherits SimPy Store)
        self.job_store = JobStore(name = f"{self.name()}_JobStore")

        # Processor resource management
        self.processor_resources = {}  # {processor_id: ProcessorResource}

        # Track completed jobs
        self.completed_jobs = []

        # Next process
        self.next_process = None
        self.available_processors = []
        self.current_jobs = 0
    def connect_to_next_process(self, next_process):
        """Connect directly to next process. Used for process initialization."""
        self.next_process = next_process

    def register_processor(self, processor):
        """Register processor (Machine or Worker). Used for process initialization."""
        # Add to processor list
        self.list_processors.append(processor)

        # Create ProcessorResource (integrated resource management)
        processor_resource = ProcessorResource(self.env, processor)

        # Determine id based on processor type
        if processor.type_processor == "Machine":
            processor_id = f"Machine_{processor.id_machine}"
        else:  # Worker
            processor_id = f"Worker_{processor.id_worker}"

        # Store resource
        self.processor_resources[processor_id] = processor_resource


       
    def process(self):
            """
            Allocate available resources (machines or workers) to jobs in queue
            """
            # print(
            #     f"[DEBUG] {self.name()}: seize_resources called, time={self.env.now}")

            # Find available processors
            self.available_processors = [
                res for res in self.processor_resources.values() if res.is_available]
            if self.name() == "Proc_Build":
                print("time:",self.env.now(), "processors:",len(self.available_processors))
            # print(
            #     f"[DEBUG] {self.name()}: available processors={len(available_processors)}")
            # Debug: Print status of each resource
            # for res_id, res in self.processor_resources.items():
            #     print(
            #         f"[DEBUG] Processor {res_id}: is_available={res.is_available}, capacity={res.capacity}")

            # If queue is empty or no available processors, stop
            if self.job_store.is_empty or not self.available_processors:
                # print(
                #     f"[DEBUG] {self.name()}: job allocation stopped - queue empty={self.job_store.is_empty}, no processors={not available_processors}")
                return
            
            # List of jobs assigned to each processor
            processor_assignments = []
            # Try processing with all processors
            for processor_resource in self.available_processors:
                # print(
                #     f"[DEBUG] {self.name()}: attempting to process with {processor_resource.name}")
                # Determine number of jobs to assign (up to capacity)
                remaining_capacity = processor_resource.num_capacity
                jobs_to_assign = []
                #print(self.env.now(),self.name(),remaining_capacity)
                # Assign jobs
                try:
                    for i in range(min(remaining_capacity, self.job_store.size)):
                        if not self.job_store.is_empty:
                            # print(
                            #     f"[DEBUG] {self.name()}: attempting to get job {i+1}")
                            job = self.job_store.from_store()
                            # print(
                            #     f"[DEBUG] {self.name()}: retrieved job {job.id_job}")
                            jobs_to_assign.append(job)
                except Exception as e:
                    # Continue if unable to get job from JobStore
                    print(f"[ERROR] {self.name()}: failed to get job: {e}")

                # Assign jobs to processor
                if jobs_to_assign:
                    processor_assignments.append(
                        (processor_resource, jobs_to_assign))
                    # yield self.env.process(self.delay_resources(processor_resource, jobs_to_assign))
            # Process jobs with assigned processors in parallel
            for processor_resource, jobs in processor_assignments:
                if self.name() == "Proc_Wash":
                    print(processor_resource._claimed_quantity)
                    print(self.name(),len(processor_assignments), processor_assignments)
                Process(self, processor_resource, jobs)
                processor_resource.num_capacity -= 1
    def add_to_queue(self, job):
        """Add job to queue"""
        job.time_waiting_start = self.env.now()
        job.workstation["Process"] = self.name()
        # Add job to JobStore
        self.job_store.add(job)
        if self.logger:
            self.logger.log_event(
                "Queue", f"Added job {job.id_job} to {self.name()} queue. Queue length: {self.job_store.size}")

        self.activate()