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
                 break_time=600,
                 accumulator_reset=660
                 ):
        self.origin = origin
        self.destination = destination
        self.break_time=break_time
        self.accumulator_reset=accumulator_reset
        if tt_od > 0:
            tt_o = accumulator_reset
            if tt_od <= accumulator_reset:
                tt_o = math.floor(tt_od/2)
            self.tt_o = int(tt_o)
            self.tt_d = int(tt_od - self.tt_o)
            #print(self.tt_o,self.tt_d,tt_od)
        else:
            self.tt_o = 0
            self.tt_d = 0

        self.node = new_node

    # FIXME this is a little bit bald
    def drive_time_restore(self):
        return -self.accumulator_reset
