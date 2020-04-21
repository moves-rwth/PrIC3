class ObligationCache:

    def __init__(self):
        self.obligation_cache = dict()


    def get_cached(self, state_id, chosen_command, delta):
        if (state_id, chosen_command, delta) in self.obligation_cache.keys():
            return self.obligation_cache[(state_id, chosen_command, delta)]

        else:
            return False

    def cache(self, state_id, chosen_command, delta, map):
        self.obligation_cache[(state_id, chosen_command, delta)] = map

    def reset_cache(self):
        self.obligation_cache = dict()
