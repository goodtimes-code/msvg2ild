import xml.sax, xml.sax.handler
from laser import LaserFrame, LaserPath
from path import PathLine, PathBezier4, PathBezier3
import re
import math


class SVGReader(xml.sax.handler.ContentHandler):
    def doctype(self, name, pubid, system):
        print(name,pubid,system)
    def startDocument(self):
        self.frame = LaserFrame()
        self.matrix_stack = [(1,0,0,1,0,0)]
        self.style_stack = []
        self.defsdepth = 0
    def endDocument(self):
        self.frame.transform(self.tc)
    def startElement(self, name, attrs):
        if name == "svg":
            self.dx = self.dy = 0
            if 'viewBox' in attrs.keys():
                self.dx, self.dy, self.width, self.height = map(float, attrs['viewBox'].split())
            else:
                ws = attrs['width']
                hs = attrs['height']
                for r in ('px','pt','mm','in','cm','%'):
                    hs = hs.replace(r,"")
                    ws = ws.replace(r,"")
                self.width = float(ws)
                self.height = float(hs)
        elif name == "path":
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                self.addPath(attrs['d'])
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name in ("polyline","polygon"):
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                self.addPolyline(attrs['points'], name == "polygon")
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name == "line":
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                x1, y1, x2, y2 = [float(attrs[x]) for x in ('x1','y1','x2','y2')]
                self.addLine(x1, y1, x2, y2)
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name == "rect":
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                x1, y1, w, h = [float(attrs[x]) for x in ('x','y','width','height')]
                self.addRect(x1, y1, x1+w, y1+h)
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name == "circle":
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                cx, cy, r = [float(attrs[x]) for x in ('cx','cy','r')]
                self.addCircle(cx, cy, r)
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name == "ellipse":
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            if self.defsdepth == 0 and self.isvisible(attrs):
                cx, cy, rx, ry = [float(attrs[x]) for x in ('cx','cy','rx','ry')]
                self.addEllipse(cx, cy, rx, ry)
            if 'transform' in attrs.keys():
                self.popmatrix()
        elif name == 'g':
            if 'transform' in attrs.keys():
                self.transform(attrs['transform'])
            else:
                self.pushmatrix((1,0,0,1,0,0))
            if 'style' in attrs.keys():
                self.style_stack.append(attrs['style'])
            else:
                self.style_stack.append("")
        elif name in ('defs','clipPath'):
            self.defsdepth += 1
    def endElement(self, name):
        if name == 'g':
            self.popmatrix()
            self.style_stack.pop()
        elif name in ('defs','clipPath'):
            self.defsdepth -= 1
    def mmul(self, m1, m2):
        a1,b1,c1,d1,e1,f1 = m1
        a2,b2,c2,d2,e2,f2 = m2
        a3 = a1 * a2 + c1 * b2
        b3 = b1 * a2 + d1 * b2
        c3 = a1 * c2 + c1 * d2
        d3 = b1 * c2 + d1 * d2
        e3 = a1 * e2 + c1 * f2 + e1
        f3 = b1 * e2 + d1 * f2 + f1
        return (a3,b3,c3,d3,e3,f3)
    def pushmatrix(self, m):
        new_mat = self.mmul(self.matrix_stack[-1], m)
        self.matrix_stack.append(new_mat)
    def popmatrix(self):
        self.matrix_stack.pop()
    def tc(self,coord):
        vw = vh = max(self.width, self.height) / 2.0
        x,y = coord
        x -= self.width / 2.0 + self.dx
        y -= self.height / 2.0 + self.dy
        x = x / vw
        y = y / vh
        return (x,y)
    def ts(self,coord):
        a,b,c,d,e,f = self.matrix_stack[-1]
        x,y = coord
        nx = a*x + c*y + e
        ny = b*x + d*y + f
        return (nx,ny)
    def transform(self, data):
        ds = re.split(r"[ \r\n\t]*([a-z]+\([^)]+\)|,)[ \r\n\t]*", data)
        tokens = []
        for v in ds:
            if v in ', \t':
                continue
            if v == '':
                continue
            if not re.match(r"[a-z]+\([^)]+\)", v):
                raise ValueError("Invalid SVG transform expression: %r (%r)"%(data,v))
            tokens.append(v)
        transforms = tokens

        mat = (1,0,0,1,0,0)
        for t in transforms:
            name,rest = t.split("(")
            if rest[-1] != ")":
                raise ValueError("Invalid SVG transform expression: %r (%r)"%(data,rest))
            args = list(map(float,re.split(r'[, \t]+',rest[:-1])))
            if name == 'matrix':
                mat = self.mmul(mat, args)
            elif name == 'translate':
                tx,ty = args
                mat = self.mmul(mat, (1,0,0,1,tx,ty))
            elif name == 'scale':
                if len(args) == 1:
                    sx,sy = args[0],args[0]
                else:
                    sx,sy = args
                mat = self.mmul(mat, (sx,0,0,sy,0,0))
            elif name == 'rotate':
                a = args[0] / 180.0 * math.pi
                if len(args) == 3:
                    cx,cy = args[1:]
                    mat = self.mmul(mat, (1,0,0,1,cx,cy))
                cos = math.cos(a)
                sin = math.sin(a)
                mat = self.mmul(mat, (cos,sin,-sin,cos,0,0))
                if len(args) == 3:
                    mat = self.mmul(mat, (1,0,0,1,-cx,-cy))
            elif name == 'skewX':
                a = args[0] / 180.0 * math.pi
                mat = self.mmul(mat, (1,0,math.tan(a),1,0,0))
            elif name == 'skewY':
                a = args[0] / 180.0 * math.pi
                mat = self.mmul(mat, (1,math.tan(a),0,1,0,0))
        self.pushmatrix(mat)
    def addPath(self, data):
        p = SVGPath(data)
        for path in p.subpaths:
            path.transform(self.ts)
            self.frame.add(path)
    def addPolyline(self, data, close=False):
        p = SVGPolyline(data, close)
        for path in p.subpaths:
            path.transform(self.ts)
            self.frame.add(path)
    def addLine(self, x1, y1, x2, y2):
        path = LaserPath()
        path.add(PathLine((x1,y1), (x2,y2)))
        path.transform(self.ts)
        self.frame.add(path)
    def addRect(self, x1, y1, x2, y2):
        path = LaserPath()
        path.add(PathLine((x1,y1), (x2,y1)))
        path.add(PathLine((x2,y1), (x2,y2)))
        path.add(PathLine((x2,y2), (x1,y2)))
        path.add(PathLine((x1,y2), (x1,y1)))
        path.transform(self.ts)
        self.frame.add(path)
    def addCircle(self, cx, cy, r):
        cp = 0.55228475 * r
        path = LaserPath()
        path.add(PathBezier4((cx,cy-r), (cx+cp,cy-r), (cx+r,cy-cp), (cx+r,cy)))
        path.add(PathBezier4((cx+r,cy), (cx+r,cy+cp), (cx+cp,cy+r), (cx,cy+r)))
        path.add(PathBezier4((cx,cy+r), (cx-cp,cy+r), (cx-r,cy+cp), (cx-r,cy)))
        path.add(PathBezier4((cx-r,cy), (cx-r,cy-cp), (cx-cp,cy-r), (cx,cy-r)))
        path.transform(self.ts)
        self.frame.add(path)
    def addEllipse(self, cx, cy, rx, ry):
        cpx = 0.55228475 * rx
        cpy = 0.55228475 * ry
        path = LaserPath()
        path.add(PathBezier4((cx,cy-ry), (cx+cpx,cy-ry), (cx+rx,cy-cpy), (cx+rx,cy)))
        path.add(PathBezier4((cx+rx,cy), (cx+rx,cy+cpy), (cx+cpx,cy+ry), (cx,cy+ry)))
        path.add(PathBezier4((cx,cy+ry), (cx-cpx,cy+ry), (cx-rx,cy+cpy), (cx-rx,cy)))
        path.add(PathBezier4((cx-rx,cy), (cx-rx,cy-cpy), (cx-cpx,cy-ry), (cx,cy-ry)))
        path.transform(self.ts)
        self.frame.add(path)
    def isvisible(self, attrs):
        # skip elements with no stroke or fill
        # hacky but gets rid of some gunk
        style = ' '.join(self.style_stack)
        if 'style' in attrs.keys():
            style += " %s"%attrs['style']
        if 'fill' in attrs.keys() and attrs['fill'] != "none":
            return True
        style = re.sub(r'fill:\s*none\s*(;?)','', style)
        style = re.sub(r'stroke:\s*none\s*(;?)','', style)
        if 'stroke' not in style and re.match(r'fill:\s*none\s',style):
            return False
        if re.match(r'display:\s*none', style):
            return False
        return True


class SVGPath(object):
    def __init__(self, data=None):
        self.subpaths = []
        if data:
            self.parse(data)

    def poptok(self):
        if not self.tokens:
            raise ValueError("Expected token but got end of path data")
        return self.tokens.pop(0)
    def peektok(self):
        if not self.tokens:
            raise ValueError("Expected token but got end of path data")
        return self.tokens[0]
    def popnum(self):
        tok = self.tokens.pop(0)
        try:
            return float(tok)
        except ValueError:
            raise ValueError("Invalid SVG path numerical token: %s"%tok)
    def isnum(self):
        if not self.tokens:
            return False # no more tokens is considered a non-number
        try:
            float(self.peektok())
        except ValueError:
            return False
        return True
    def popcoord(self,rel=False, cur=None):
        x = self.popnum()
        if self.peektok() == ',':
            self.poptok()
        y = self.popnum()
        if rel:
            x += cur[0]
            y += cur[1]
        return x,y
    def reflect(self, center, point):
        cx,cy = center
        px,py = point
        return (2*cx-px, 2*cy-py)

    def angle(self, u, v):
        # calculate the angle between two vectors
        ux, uy = u
        vx, vy = v
        dot = ux*vx + uy*vy
        ul = math.sqrt(ux**2 + uy**2)
        vl = math.sqrt(vx**2 + vy**2)
        a = math.acos(dot/(ul*vl))
        return math.copysign(a, ux*vy - uy*vx)
    def arc_eval(self, cx, cy, rx, ry, phi, w):
        # evaluate a point on an arc
        x = rx * math.cos(w)
        y = ry * math.sin(w)
        x, y = x*math.cos(phi) - y*math.sin(phi), math.sin(phi)*x + math.cos(phi)*y
        x += cx
        y += cy
        return (x,y)
    def arc_deriv(self, rx, ry, phi, w):
        # evaluate the derivative of an arc
        x = -rx * math.sin(w)
        y = ry * math.cos(w)
        x, y = x*math.cos(phi) - y*math.sin(phi), math.sin(phi)*x + math.cos(phi)*y
        return (x,y)
    def arc_to_beziers(self, cx, cy, rx, ry, phi, w1, dw):
        # convert an SVG arc to 1-4 bezier segments
        segcnt = min(4,int(abs(dw) / (math.pi/2) - 0.00000001) + 1)
        beziers = []
        for i in range(segcnt):
            sw1 = w1 + dw / segcnt * i
            sdw = dw / segcnt
            p0 = self.arc_eval(cx, cy, rx, ry, phi, sw1)
            p3 = self.arc_eval(cx, cy, rx, ry, phi, sw1+sdw)
            a = math.sin(sdw)*(math.sqrt(4+3*math.tan(sdw/2)**2)-1)/3
            d1 = self.arc_deriv(rx, ry, phi, sw1)
            d2 = self.arc_deriv(rx, ry, phi, sw1+sdw)
            p1 = p0[0] + a*d1[0], p0[1] + a*d1[1]
            p2 = p3[0] - a*d2[0], p3[1] - a*d2[1]
            beziers.append(PathBezier4(p0, p1, p2, p3))
        return beziers
    def svg_arc_to_beziers(self, start, end, rx, ry, phi, fa, fs):
        # first convert endpoint format to center-and-radii format
        rx, ry = abs(rx), abs(ry)
        phi = phi % (2*math.pi)

        x1, y1 = start
        x2, y2 = end
        x1p = (x1 - x2) / 2
        y1p = (y1 - y2) / 2
        psin = math.sin(phi)
        pcos = math.cos(phi)
        x1p, y1p = pcos*x1p + psin*y1p, -psin*x1p + pcos*y1p
        foo = x1p**2 / rx**2 + y1p**2 / ry**2
        sr = ((rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2) /
                    (rx**2 * y1p**2 + ry**2 * x1p**2))
        if foo > 1 or sr < 0:
            #print "fixup!",foo,sr
            rx = math.sqrt(foo)*rx
            ry = math.sqrt(foo)*ry
            sr = 0

        srt = math.sqrt(sr)
        if fa == fs:
            srt = -srt
        cxp, cyp = srt * rx * y1p / ry, -srt * ry * x1p / rx
        cx, cy = pcos*cxp + -psin*cyp, psin*cxp + pcos*cyp
        cx, cy = cx + (x1+x2)/2, cy + (y1+y2)/2

        va = ((x1p - cxp)/rx, (y1p - cyp)/ry)
        vb = ((-x1p - cxp)/rx, (-y1p - cyp)/ry)
        w1 = self.angle((1,0), va)
        dw = self.angle(va, vb) % (2*math.pi)
        if not fs:
            dw -= 2*math.pi

        # then do the actual approximation
        return self.arc_to_beziers(cx, cy, rx, ry, phi, w1, dw)

    def parse(self, data):
        ds = re.split(r"[ \r\n\t]*([-+]?\d+\.\d+[eE][+-]?\d+|[-+]?\d+\.\d+|[-+]?\.\d+[eE][+-]?\d+|[-+]?\.\d+|[-+]?\d+\.?[eE][+-]?\d+|[-+]?\d+\.?|[MmZzLlHhVvCcSsQqTtAa])[, \r\n\t]*", data)
        tokens = ds[1::2]
        if any(ds[::2]) or not all(ds[1::2]):
            raise ValueError("Invalid SVG path expression: %r"%data)
        self.tokens = tokens

        cur = (0,0)
        curcpc = (0,0)
        curcpq = (0,0)
        sp_start = (0,0)
        in_path = False
        cmd = None
        subpath = LaserPath()
        while tokens:
            if self.isnum() and cmd in "MmLlHhVvCcSsQqTtAa":
                pass
            elif self.peektok() in "MmZzLlHhVvCcSsQqTtAa":
                cmd = tokens.pop(0)
            else:
                raise ValueError("Invalid SVG path token %s"%tok)

            rel = cmd.upper() != cmd
            ucmd = cmd.upper()

            if not in_path and ucmd != 'M' :
                raise ValueErorr("SVG path segment must begin with 'm' command, not '%s'"%cmd)

            if ucmd == 'M':
                sp_start = self.popcoord(rel, cur)
                if subpath.segments:
                    self.subpaths.append(subpath)
                subpath = LaserPath()
                cmd = 'Ll'[rel]
                cur = curcpc = curcpq = sp_start
                in_path = True
            elif ucmd == 'Z':
                print(sp_start, cur)
                if (sp_start[0] - cur[0]) > 0.0000001 or (sp_start[1] - cur[1]) > 0.0000001:
                    subpath.add(PathLine(cur, sp_start))
                cur = curcpc = curcpq = sp_start
                subpath.segments[-1].end = subpath.segments[0].start
                in_path = False
            elif ucmd == 'L':
                end = self.popcoord(rel, cur)
                subpath.add(PathLine(cur, end))
                cur = curcpc = curcpq = end
            elif ucmd == 'H':
                ex = self.popnum()
                if rel:
                    ex += cur[0]
                end = ex,cur[1]
                subpath.add(PathLine(cur, end))
                cur = curcpc = curcpq = end
            elif ucmd == 'V':
                ey = self.popnum()
                if rel:
                    ey += cur[1]
                end = cur[0],ey
                subpath.add(PathLine(cur, end))
                cur = curcpc = curcpq = end
            elif ucmd in 'CS':
                if ucmd == 'S':
                    c1 = self.reflect(cur,curcpc)
                else:
                    c1 = self.popcoord(rel, cur)
                c2 = curcpc = self.popcoord(rel, cur)
                end = self.popcoord(rel, cur)
                subpath.add(PathBezier4(cur, c1, c2, end))
                cur = curcpq = end
            elif ucmd in 'QT':
                if ucmd == 'T':
                    cp = curcpq = self.reflect(cur,curcpq)
                else:
                    cp = curcpq = self.popcoord(rel, cur)
                end = self.popcoord(rel, cur)
                subpath.add(PathBezier3(cur, cp, end))
                cur = curcpc = end
            elif ucmd == 'A':
                rx, ry = self.popcoord()
                phi = self.popnum() / 180.0 * math.pi
                fa = self.popnum() != 0
                fs = self.popnum() != 0
                end = self.popcoord(rel, cur)

                if cur == end:
                    cur = curcpc = curcpq = end
                    continue
                if rx == 0 or ry == 0:
                    subpath.add(PathLine(cur, end))
                    cur = curcpc = curcpq = end
                    continue

                subpath.segments += self.svg_arc_to_beziers(cur, end, rx, ry, phi, fa, fs)
                cur = curcpc = curcpq = end

        if subpath.segments:
            self.subpaths.append(subpath)

class SVGPolyline(SVGPath):
    def __init__(self, data=None, close=False):
        self.subpaths = []
        if data:
            self.parse(data, close)
    def parse(self, data, close=False):
        ds = re.split(r"[ \r\n\t]*([-+]?\d+\.\d+[eE][+-]?\d+|[-+]?\d+\.\d+|[-+]?\.\d+[eE][+-]?\d+|[-+]?\.\d+|[-+]?\d+\.?[eE][+-]?\d+|[-+]?\d+\.?)[, \r\n\t]*", data)
        tokens = ds[1::2]
        if any(ds[::2]) or not all(ds[1::2]):
            raise ValueError("Invalid SVG path expression: %r"%data)

        self.tokens = tokens
        cur = None
        first = None
        subpath = LaserPath()
        while tokens:
            pt = self.popcoord()
            if first is None:
                first = pt
            if cur is not None:
                subpath.add(PathLine(cur, pt))
            cur = pt
        if close:
            subpath.add(PathLine(cur, first))
        self.subpaths.append(subpath)