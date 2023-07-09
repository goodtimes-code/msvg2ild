#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys
import struct
import xml.sax, xml.sax.handler
from render_parameters import RenderParameters
from svg import SVGReader


def pc(c):
    x,y = c
    if isinstance(x,int) and isinstance(y,int):
        return "(%d,%d)"%(x,y)
    else:
        return "(%.4f, %.4f)"%(x,y)

def load_svg(path):
    handler = SVGReader()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.parse(path)
    return handler.frame

def write_ild(params, rframes, path, center=True):
    fout = open(path, "wb")
    total_frames = len(rframes)
    
    for frame_index, rframe in enumerate(rframes):
        min_x = min_y = max_x = max_y = None
        for i, sample in enumerate(rframe):
            x, y = sample.coord
            if min_x is None or min_x > x:
                min_x = x
            if min_y is None or min_y > y:
                min_y = y
            if max_x is None or max_x < x:
                max_x = x
            if max_y is None or max_y < y:
                max_y = y

        for i, sample in enumerate(rframe):
            if sample.on:
                rframe = rframe[:i] + [sample]*params.extra_first_dwell + rframe[i+1:]
                break

        if len(rframe) == 0:
            raise ValueError("No points rendered")

        if center:
            offx = -(min_x + max_x)/2
            offy = -(min_y + max_y)/2
            width = max_x - min_x
            height = max_y - min_y
        else:
            offx = 0
            offy = 0
            width = 2*max(abs(min_x), abs(max_x))
            height = 2*max(abs(min_y), abs(max_y))

        scale = 1

        if width > 65534 or height > 65534:
            smax = max(width, height)
            scale = 65534.0/smax
            print("Scaling to %.02f%% due to overflow"%(scale*100))

        if len(rframe) >= 65535:
            raise ValueError("Too many points (%d, max 65535)"%len(rframe))

        samples = len(rframe)

        dout = b""
        for i, sample in enumerate(rframe):
            x, y = sample.coord
            x += offx
            y += offy
            x *= scale
            y *= scale
            x = int(x)
            y = int(y)
            mode = 0
            if i == len(rframe) - 1:
                mode |= 0x80
            if params.invert:
                sample.on = not sample.on
            if params.force:
                sample.on = True
            if not sample.on:
                mode |= 0x40
            if abs(x) > 32767:
                raise ValueError("X out of bounds: %d"%x)
            if abs(y) > 32767:
                raise ValueError("Y out of bounds: %d"%y)
            dout += struct.pack(">hhBB",x,-y,mode,0x01 if sample.on else 0x00)

        hdr = struct.pack(">4s3xB8s8sHHHBx", b"ILDA", 1, b"svg2ilda", b"", samples, frame_index, total_frames, 0)
        fout.write(hdr)
        fout.write(dout)
    hdr = struct.pack(">4s3xB8s8sHHHBx", b"ILDA", 0, b"svg2ilda", b"", 0, 0, total_frames, 0)
    fout.write(hdr)
    fout.close()

if __name__ == "__main__":
    optimize = True
    verbose = True
    center = True
    params = RenderParameters()

    if sys.argv[1] == "-q":
        verbose = False
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    if sys.argv[1] == "-noopt":
        optimize = False
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    if sys.argv[1] == "-noctr":
        center = False
        sys.argv = [sys.argv[0]] + sys.argv[2:]

    if sys.argv[1] == "-cfg":
        params.load(sys.argv[2])
        sys.argv = [sys.argv[0]] + sys.argv[3:]

    svg_directory = sys.argv[1]
    svg_files = sorted([f for f in os.listdir(svg_directory) if f.endswith('.svg')])

    rframes = []

    for svg_file in svg_files:
        svg_path = os.path.join(svg_directory, svg_file)
        if verbose:
            print(f"Parse {svg_file}")
        frame = load_svg(svg_path)
        if verbose:
            print("Done")

        if optimize:
            frame.sort()

        if verbose:
            print("Render")
        rframe = frame.render(params)
        rframes.append(rframe)
        if verbose:
            print("Done")

    write_ild(params, rframes, sys.argv[2], center)
