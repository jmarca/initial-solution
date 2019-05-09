import math

class BreakNode():
    """
    A class for modeling break nodes
    """
    def __init__(self,
                 origin, # where from
                 destination, # where to
                 tt_od, # travel time origin to destination
                 new_node=0, # the numbering of the new node
                 break_count=1
                 ):
        self.origin = origin
        self.destination = destination
        self.tt_o = math.floor(tt_od/2)
        self.tt_d = int(tt_od - self.tt_o)
        self.node = new_node
        self.break_count = break_count

    # FIXME this is a little bit bald
    def drive_time_restore(self):
        return -660
