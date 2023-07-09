import math
from path import PathLine


class LaserFrame(object):
    def __init__(self):
        self.objects = []
    def add(self, obj):
        self.objects.append(obj)
    def transform(self, func):
        for i in self.objects:
            i.transform(func)
    def render(self, params):
        if not self.objects:
            return []
        out = []
        for n,i in enumerate(self.objects):
            params.objects += 1
            out += i.render(params)
            cpos = out[-1].coord[0] / params.width, out[-1].coord[1] / params.height
            npos = self.objects[(n+1) % len(self.objects)].startpos()
            trip = [LaserSample((int(cpos[0]*params.width),int(cpos[1]*params.height)))] * params.switch_on_dwell
            trip += PathLine(cpos,npos,False).render(params)
            trip += [LaserSample((int(npos[0]*params.width),int(npos[1]*params.height)))] * params.switch_off_dwell
            params.points_dwell_switch += params.switch_on_dwell + params.switch_off_dwell
            for s in trip:
                s.on = False
            out += trip
        params.points = len(out)
        params.points_on = sum([int(s.on) for s in out])
        return out
    def sort(self):
        oobj = []
        cx,cy = 0,0
        while self.objects:
            best = 99999
            besti = 0
            bestr = False
            for i,o in enumerate(self.objects):
                x,y = o.startpos()
                d = (x-cx)**2 + (y-cy)**2
                if d < best:
                    best = d
                    besti = i
                x,y = o.endpos()
                d = (x-cx)**2 + (y-cy)**2
                if d < best:
                    best = d
                    besti = i
                    bestr = True
            obj = self.objects.pop(besti)
            if bestr:
                obj = obj.reverse()
            oobj.append(obj)
            cx,cy = obj.endpos()
        self.objects = oobj
    def showinfo(self, tr=''):
        print(tr+'LaserFrame:')
        for i in self.objects:
            i.showinfo(tr+' ')

class LaserSample(object):
    def __init__(self, coord, on=True):
        self.coord = coord
        self.on = on
    def __str__(self):
        return "[%d] %d,%d"%(int(self.on),self.coord[0],self.coord[1])
    def __repr__(self):
        return "LaserSample((%d,%d),%r)"%(self.coord[0],self.coord[1],self.on)

class LaserPath(object):
    def __init__(self):
        self.segments = []
    def add(self, seg):
        self.segments.append(seg)
    def transform(self, func):
        for i in self.segments:
            i.transform(func)
    def render(self, params):
        is_closed = self.segments[0].start == self.segments[-1].end
        sx,sy = self.segments[0].start
        out = []
        if is_closed:
            out += [LaserSample((int(sx*params.width),int(sy*params.height)))] * params.closed_start_dwell
        else:
            out += [LaserSample((int(sx*params.width),int(sy*params.height)))] * params.start_dwell
        params.points_dwell_start += params.start_dwell
        for i,s in enumerate(self.segments):
            params.subpaths += 1
            out += s.render(params)
            ex,ey = s.end
            end_render = [LaserSample((int(ex*params.width),int(ey*params.height)))]
            if i != len(self.segments)-1:
                ecx,ecy = s.ecp()
                sx,sy = self.segments[i+1].start
                scx,scy = self.segments[i+1].scp()

                dex,dey = ecx-ex,ecy-ey
                dsx,dsy = sx-scx,sy-scy

                dot = dex*dsx + dey*dsy
                lens = math.sqrt(dex**2 + dey**2) * math.sqrt(dsx**2 + dsy**2)
                if lens == 0:
                    # bail
                    out += end_render * params.corner_dwell
                    params.points_dwell_corner += params.corner_dwell
                else:
                    dot /= lens
                    curve_angle = math.cos(params.curve_angle*(math.pi/180.0))
                    if dot > curve_angle:
                        out += end_render * params.curve_dwell
                        params.points_dwell_curve += params.curve_dwell
                    else:
                        out += end_render * params.corner_dwell
                        params.points_dwell_corner += params.corner_dwell
            elif is_closed:
                overdraw = out[:params.closed_overdraw]
                out += overdraw
                out += [out[-1]] * params.closed_end_dwell
                params.points_dwell_end += params.closed_end_dwell
            else:
                out += end_render * params.end_dwell
                params.points_dwell_end += params.end_dwell
        return out
    def startpos(self):
        return self.segments[0].start
    def endpos(self):
        return self.segments[-1].end
    def reverse(self):
        lp = LaserPath()
        lp.segments = [x.reverse() for x in self.segments[::-1]]
        return lp
    def showinfo(self, tr=''):
        print(tr+'LaserPath:')
        for i in self.segments:
            i.showinfo(tr+' ')