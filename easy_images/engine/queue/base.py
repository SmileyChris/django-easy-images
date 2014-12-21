PRIORITY_CRITICAL = 3
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 1
PRIORITY_LOW = 0


class BaseQueue(object):

    def add(self, action, priority=PRIORITY_NORMAL, **kwargs):
        """
        This method should add the item to a queue.
        """
        self.start_processing(action)
        if priority == PRIORITY_CRITICAL:
            result = self.generate(action)
            self.finished_processing(action)
            return result
        return self.add_to_queue(action=action, priority=priority, **kwargs)

    def add_to_queue(self, action, **kwargs):
        raise NotImplementedError()

    def processing(self, key, **kwargs):
        """
        Check to see if this key is on the queue already.

        This method must be overridden in a subclass.
        """
        raise NotImplementedError()

    def start_processing(self, action, **kwargs):
        """
        Hook to record that processing has started for all the options provided
        in the action message.

        This method must be overridden in a subclass.
        """
        raise NotImplementedError()

    def finished_processing(self, action, **kwargs):
        """
        Hook to allow for any actions after generation is complete (commonly
        used to update a record for the "is processing" logic).

        By default, this hook does nothing.
        """
        return

    def get_keys(self, action):
        keys = []
        for opts in action['all_opts'].values():
            key = opts.get('KEY')
            if key:
                keys.append(key)
        return keys
