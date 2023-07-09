

class RenderParameters(object):
    def __init__(self):
        # output sample rate
        self.rate = 48000
        # time to display (seconds)
        # use 0.0 for a single frame
        self.time = 0.0
        # step size of galvo movement, in fractions of output size per sample (2=full width)
        self.on_speed = 2/90.0
        # same, but for "off" laser state
        self.off_speed = 2/20.0
        # bound for accurate bezier rendering (lower = better)
        self.flatness = 0.000002
        # output render size (max 32767)
        self.width = 32767
        self.height = 32767
        # angle below which a node is considered smooth
        self.curve_angle = 30.0
        # dwell time at the start of a path (samples)
        self.start_dwell = 3
        # dwell time on internal curved nodes (samples)
        self.curve_dwell = 0
        # dwell time on internal corner nodes (samples)
        self.corner_dwell = 4
        # dwell time at the end of a path (samples)
        self.end_dwell = 3
        # dwell time before switching the beam on, and after switching it off
        self.switch_on_dwell = 3
        self.switch_off_dwell = 6
        # how many pointer of overdraw for closed shapes
        self.closed_overdraw = 0
        self.closed_start_dwell = 3
        self.closed_end_dwell = 3
        # extra dwell for the first active pointer
        self.extra_first_dwell = 0
        # invert image (show inter-object trips)
        self.invert = False
        self.force = False

        self.reset_stats()
    def reset_stats(self):
        self.rate_divs = 0
        self.flatness_divs = 0
        self.objects = 0
        self.subpaths = 0
        self.points = 0
        self.points_line = 0
        self.points_trip = 0
        self.points_bezier = 0
        self.points_dwell_start = 0
        self.points_dwell_curve = 0
        self.points_dwell_corner = 0
        self.points_dwell_end = 0
        self.points_dwell_switch = 0
        self.points_on = 0

    def load(self, f):
        for line in open(f):
            line = line.replace("\n","").strip()
            if line=="":
                continue
            var, val = line.split("=",1)
            var = var.strip()
            val = val.strip()
            self.__setattr__(var, eval(val))