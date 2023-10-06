import threading


class TaskController:
    def __init__(self, start_button, stop_button, function):
        self.task_thread = None
        self.stop_thread_flag = False
        self.function = function
        self.shared_variable = threading.Event()

        self.start_button = start_button
        self.stop_button = stop_button

        # start_button.on_event("click", self.start_task)
        stop_button.on_event("click", self.stop_task)

    def long_running_task(self):
        self.function(self.shared_variable)
        self.start_button.loading = False

    def start_task(self, *args):
        self.stop_thread_flag = False
        self.shared_variable.clear()
        self.start_button.loading = True
        self.task_thread = threading.Thread(target=self.long_running_task)
        self.task_thread.start()
        self.task_thread.join()

    def stop_task(self, *args):
        self.stop_button.loading = True
        self.stop_thread_flag = True
        self.shared_variable.set()
        if self.task_thread is not None:
            self.task_thread.join()
        self.start_button.loading = False
        self.stop_button.loading = False
        print("Task thread stopped.")
