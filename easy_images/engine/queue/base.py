import abc

PRIORITY_CRITICAL = 3
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 1
PRIORITY_LOW = 0


class BaseQueue(object):

    def add(self, action, priority=PRIORITY_NORMAL, **kwargs):
        """
        Add the item to a queue unless critical priority, in which case
        generate the image instantly.
        """
        self.start_processing(action)
        if priority == PRIORITY_CRITICAL:
            result = self.generate_and_record(action)
            self.finished_processing(action)
            return result
        return self.add_to_queue(action=action, priority=priority, **kwargs)

    @abc.abstractmethod
    def add_to_queue(self, action, **kwargs):
        """
        Add an action to the queue.
        """

    @abc.abstractmethod
    def processing(self, key, **kwargs):
        """
        Check to see if this key is on the queue already.
        """

    @abc.abstractmethod
    def start_processing(self, action, **kwargs):
        """
        Hook to record that processing has started for all the options provided
        in the action message.
        """

    def finished_processing(self, action, **kwargs):
        """
        Hook to allow for any actions after generation is complete (commonly
        used to update a record for the "is processing" logic).

        By default, this hook does nothing.
        """
        return

    def get_keys(self, action):
        """
        Utility method to retrieve all the keys from an action.
        """
        keys = []
        for opts in action['all_opts'].values():
            key = opts.get('KEY')
            if key:
                keys.append(key)
        return keys
