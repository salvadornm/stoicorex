#!/usr/bin/env python3

import os
import numpy as np
import yt

HEADER_FILE = "Header"
DATA_FILE = "Level_0/DATA_00000"


def read_amrex_particle_header(filename=HEADER_FILE):
    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    version = lines[0]
    ndim = int(lines[1])
    nreal = int(lines[2])
    real_names = lines[3 : 3 + nreal]

    nint = int(lines[3 + nreal])
    nlev = int(lines[4 + nreal])
    npart_total = int(lines[5 + nreal])
    next_id = int(lines[6 + nreal])

    return {
        "version": version,
        "ndim": ndim,
        "nreal": nreal,
        "real_names": real_names,
        "nint": nint,
        "nlev": nlev,
        "npart_total": npart_total,
        "next_id": next_id,
    }


def read_amrex_particle_data(header, data_filename=DATA_FILE):
    npart = header["npart_total"]
    nreal = header["nreal"]

    filesize = os.path.getsize(data_filename)

    # We know from your file: 80 bytes/particle.
    # We read 3 (x,y,z) + nreal doubles = 3 + 6 = 9 doubles = 72 bytes.
    n_doubles_per_particle = 3 + nreal
    bytes_per_particle_we_read = n_doubles_per_particle * 8

    if bytes_per_particle_we_read > filesize // npart:
        raise RuntimeError(
            f"Not enough bytes per particle to read {n_doubles_per_particle} doubles "
            f"(file has {filesize // npart} bytes/particle)."
        )

    total_doubles_to_read = npart * n_doubles_per_particle

    with open(data_filename, "rb") as f:
        arr = np.fromfile(f, dtype=np.float64, count=total_doubles_to_read)

    if arr.size != total_doubles_to_read:
        raise RuntimeError(
            f"Expected {total_doubles_to_read} doubles, got {arr.size}. "
            "File may be truncated."
        )

    return arr.reshape((npart, n_doubles_per_particle))


def main():
    # 1. Header
    header = read_amrex_particle_header(HEADER_FILE)
    print("Header info:")
    for k, v in header.items():
        print(f"  {k}: {v}")

    # 2. Binary data
    data = read_amrex_particle_data(header, DATA_FILE)
    npart = header["npart_total"]
    nreal = header["nreal"]
    real_names = header["real_names"]

    print(f"\nRead particle data: {npart} particles, {nreal} real components")
    print("Real component names:", real_names)

    x = data[:, 0]
    y = data[:, 1]
    z = data[:, 2]
    reals = data[:, 3:]  # shape (npart, nreal)

    # 3. Build a yt dataset from particles
    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()
    zmin, zmax = z.min(), z.max()

    pad = 0.05
    bbox = np.array(
        [
            [xmin - pad * (xmax - xmin if xmax > xmin else 1.0),
             xmax + pad * (xmax - xmin if xmax > xmin else 1.0)],
            [ymin - pad * (ymax - ymin if ymax > ymin else 1.0),
             ymax + pad * (ymax - ymin if ymax > ymin else 1.0)],
            [zmin - pad * (zmax - zmin if zmax > zmin else 1.0),
             zmax + pad * (zmax - zmin if zmax > zmin else 1.0)],
        ]
    )

    ptype = "io"
    data_dict = {
        (ptype, "particle_position_x"): x,
        (ptype, "particle_position_y"): y,
        (ptype, "particle_position_z"): z,
    }
    for i, name in enumerate(real_names):
        data_dict[(ptype, f"particle_{name}")] = reals[:, i]

    # This is the modern, supported API in yt 4.x
    ds = yt.load_particles(data_dict, bbox=bbox, length_unit="cm")
    print("\n=== yt particle dataset created ===")
    print("Dataset:", ds)
    print("Domain left edge:", ds.domain_left_edge)
    print("Domain right edge:", ds.domain_right_edge)

    ad = ds.all_data()
    npart_ds = ad[ptype, "particle_position_x"].size
    print("\nNumber of particles in yt dataset:", int(npart_ds))

    print("\nFirst 5 particles (x,y,z):")
    for i in range(min(5, npart_ds)):
        print(
            f"{i}: ({ad[ptype,'particle_position_x'][i].v:.6e}, "
            f"{ad[ptype,'particle_position_y'][i].v:.6e}, "
            f"{ad[ptype,'particle_position_z'][i].v:.6e})"
        )

    print("\nFirst 5 of each real component:")
    for name in real_names:
        arr = ad[ptype, f"particle_{name}"]
        print(f"  particle_{name}: ", [f"{arr[i].v:.3e}" for i in range(min(5, npart_ds))])

    # 4. Simple x–y scatter
    try:
        import matplotlib.pyplot as plt

        max_points = 20000
        if npart_ds > max_points:
            idx = np.random.choice(np.arange(npart_ds), size=max_points, replace=False)
        else:
            idx = np.arange(npart_ds)

        xs = ad[ptype, "particle_position_x"][idx].v
        ys = ad[ptype, "particle_position_y"][idx].v

        plt.figure()
        plt.scatter(xs, ys, s=1)
        plt.xlabel("x [cm]")
        plt.ylabel("y [cm]")
        plt.title(f"Particle positions (N={len(idx)})")
        plt.tight_layout()
        plt.savefig("particle_xy.png")
        print("\nSaved scatter plot to particle_xy.png")
    except Exception as e:
        print("\nCould not make scatter plot:", e)


if __name__ == "__main__":
    main()

