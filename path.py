import math


class PathLine(object):
    def __init__(self, start, end, on=True):
        self.start = start
        self.end = end
        self.on = on
    def copy(self):
        return PathLine(self.start, self.end)
    def transform(self, func):
        self.start = func(self.start)
        self.end = func(self.end)
    def render(self, params):
        from laser import LaserSample

        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = math.sqrt(dx**2 + dy**2)
        if self.on:
            steps = int(length / params.on_speed) + 1
        else:
            steps = int(length / params.off_speed) + 1
        dx /= steps
        dy /= steps
        out = []
        for i in range(1, steps+1):
            x = self.start[0] + i * dx
            y = self.start[1] + i * dy
            out.append(LaserSample((int(x*params.width),int(y*params.height)), self.on))
            if self.on:
                params.points_line += 1
            else:
                params.points_trip += 1
        return out
    def reverse(self):
        return PathLine(self.end, self.start, self.on)
    def scp(self):
        return self.end
    def ecp(self):
        return self.start
    def showinfo(self, tr=''):
        print(tr+'Line( %s %s )'%(pc(self.start),pc(self.end)))

class PathBezier3(object):
    def __init__(self, start, cp, end):
        self.start = start
        self.end = end
        self.cp = cp
    def copy(self):
        return PathBezier3(self.start, self.cp, self.end)
    def transform(self, func):
        self.start = func(self.start)
        self.cp = func(self.cp)
        self.end = func(self.end)
    def render(self, params):
        # just use PathBezier4, meh
        sx,sy = self.start
        cx,cy = self.cp
        ex,ey = self.end

        c1x = (1.0/3) * cx + (2.0/3) * sx
        c1y = (1.0/3) * cy + (2.0/3) * sy
        c2x = (1.0/3) * cx + (2.0/3) * ex
        c2y = (1.0/3) * cy + (2.0/3) * ey
        return PathBezier4(self.start, (c1x,c1y), (c2x,c2y), self.end).render()
    def reverse(self):
        return PathBezier3(self.end, self.cp, self.start)
    def scp(self):
        return self.cp
    def ecp(self):
        return self.cp
    def showinfo(self, tr=''):
        print(tr+'Bezier( %s %s %s )'%(pc(self.start),pc(self.cp),pc(self.end)))

class PathBezier4(object):
    def __init__(self, start, cp1, cp2, end):
        self.start = start
        self.end = end
        self.cp1 = cp1
        self.cp2 = cp2
    def copy(self):
        return PathBezier4(self.start, self.cp1, self.cp2, self.end)
    def transform(self, func):
        self.start = func(self.start)
        self.cp1 = func(self.cp1)
        self.cp2 = func(self.cp2)
        self.end = func(self.end)

    def render(self, params):
        from laser import LaserSample

        x0,y0 = self.start
        x1,y1 = self.cp1
        x2,y2 = self.cp2
        x3,y3 = self.end
        dx = x3-x0
        dy = y3-y0
        length = math.sqrt((dx**2) + (dy**2))
        subdivide = False
        if length > params.on_speed:
            subdivide = True
            params.rate_divs += 1
        else:
            ux = (3.0*x1 - 2.0*x0 - x3)**2
            uy = (3.0*y1 - 2.0*y0 - y3)**2
            vx = (3.0*x2 - 2.0*x3 - x0)**2
            vy = (3.0*y2 - 2.0*y3 - y0)**2
            if ux < vx:
                ux = vx
            if uy < vy:
                uy = vy
            if (ux+uy) > params.flatness:
                subdivide = True
                params.flatness_divs += 1
        if subdivide:
            # de Casteljau at t=0.5
            mcx = (x1 + x2) * 0.5
            mcy = (y1 + y2) * 0.5
            ax1 = (x0 + x1) * 0.5
            ay1 = (y0 + y1) * 0.5
            ax2 = (ax1 + mcx) * 0.5
            ay2 = (ay1 + mcy) * 0.5
            bx2 = (x2 + x3) * 0.5
            by2 = (y2 + y3) * 0.5
            bx1 = (bx2 + mcx) * 0.5
            by1 = (by2 + mcy) * 0.5
            xm = (ax2 + bx1) * 0.5
            ym = (ay2 + by1) * 0.5
            curve1 = PathBezier4((x0,y0),(ax1,ay1),(ax2,ay2),(xm,ym))
            curve2 = PathBezier4((xm,ym),(bx1,by1),(bx2,by2),(x3,y3))
            return curve1.render(params) + curve2.render(params)
        else:
            params.points_bezier += 1
            return [LaserSample((int(x3*params.width),int(y3*params.height)))]
    def reverse(self):
        return PathBezier4(self.end, self.cp2, self.cp1, self.start)
    def scp(self):
        if self.cp1 != self.start:
            return self.cp1
        elif self.cp2 != self.start:
            return self.cp2
        else:
            return self.end
    def ecp(self):
        if self.cp2 != self.end:
            return self.cp2
        elif self.cp1 != self.end:
            return self.cp1
        else:
            return self.start
    def showinfo(self, tr=''):
        print(tr+'Bezier( %s %s %s %s )'%(pc(self.start),pc(self.cp1),pc(self.cp2),pc(self.end)))