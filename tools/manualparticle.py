#!/usr/bin/env python3

import os
import numpy as np
import yt

# Try to import load_particles from the stream frontend (yt >=4),
# fall back to yt.load_particles if available.
try:
    from yt.frontends.stream.data_structures import load_particles
except Exception:
    load_particles = yt.load_particles


HEADER_FILE = "Header"
DATA_FILE = "DATA_00000"


def read_amrex_particle_header(filename=HEADER_FILE):
    """
    Read the AMReX particle Header file (Version_Two_Dot_One_double)
    and return basic info + real component names.
    """
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

    # The rest is per-level / per-grid info, which we don't strictly need
    header_info = {
        "version": version,
        "ndim": ndim,
        "nreal": nreal,
        "real_names": real_names,
        "nint": nint,
        "nlev": nlev,
        "npart_total": npart_total,
        "next_id": next_id,
    }
    return header_info


def read_amrex_particle_data(header, data_filename=DATA_FILE):
    """
    Read the AMReX particle DATA_00000 file, assuming:
    - native endian float64 for positions + real components
    - each particle has: 3 coords + nreal real comps, all doubles
    - trailing 8 bytes per particle (likely id/cpu) are ignored
    """
    npart = header["npart_total"]
    nreal = header["nreal"]

    # Size of the file
    filesize = os.path.getsize(data_filename)

    # From your files: filesize / npart = 80 bytes per particle
    # We read only the first (3 + nreal) doubles = 9 doubles = 72 bytes.
    # The remaining 8 bytes per particle (id/cpu) we ignore.
    n_doubles_per_particle = 3 + nreal
    bytes_per_particle_we_read = n_doubles_per_particle * 8

    if bytes_per_particle_we_read > filesize // npart:
        raise RuntimeError(
            f"Not enough bytes per particle to read {n_doubles_per_particle} doubles "
            f"(file has {filesize // npart} bytes/particle)."
        )

    total_doubles_to_read = npart * n_doubles_per_particle

    # Read only the doubles we care about
    with open(data_filename, "rb") as f:
        arr = np.fromfile(f, dtype=np.float64, count=total_doubles_to_read)

    if arr.size != total_doubles_to_read:
        raise RuntimeError(
            f"Expected {total_doubles_to_read} doubles, got {arr.size}. "
            "File may be truncated."
        )

    arr = arr.reshape((npart, n_doubles_per_particle))
    # columns: x, y, z, real0, real1, ..., real(nreal-1)
    return arr


def main():
    # --------------------------------------------------------------
    # 1. Read header
    # --------------------------------------------------------------
    header = read_amrex_particle_header(HEADER_FILE)
    print("Header info:")
    for k, v in header.items():
        print(f"  {k}: {v}")

    # --------------------------------------------------------------
    # 2. Read binary particle data
    # --------------------------------------------------------------
    data = read_amrex_particle_data(header, DATA_FILE)
    npart = header["npart_total"]
    nreal = header["nreal"]
    real_names = header["real_names"]

    print(f"\nRead particle data: {npart} particles, {nreal} real components")
    print("Real component names:", real_names)

    # Extract positions and real comps
    x = data[:, 0]
    y = data[:, 1]
    z = data[:, 2]
    reals = data[:, 3:]  # shape (npart, nreal)

    # --------------------------------------------------------------
    # 3. Build a yt particle dataset via stream frontend
    # --------------------------------------------------------------
    # Define a bounding box from the actual particle positions
    # (add 5% padding on each side)
    xmin, xmax = x.min(), x.max()
    ymin, ymax = y.min(), y.max()
    zmin, zmax = z.min(), z.max()

    pad_x = 0.05 * (xmax - xmin if xmax > xmin else 1.0)
    pad_y = 0.05 * (ymax - ymin if ymax > ymin else 1.0)
    pad_z = 0.05 * (zmax - zmin if zmax > zmin else 1.0)

    bbox = np.array(
        [
            [xmin - pad_x, xmax + pad_x],
            [ymin - pad_y, ymax + pad_y],
            [zmin - pad_z, zmax + pad_z],
        ]
    )

    # yt particle type name
    ptype = "io"

    # Build field dict
    pt_data = {
        (ptype, "particle_position_x"): x,
        (ptype, "particle_position_y"): y,
        (ptype, "particle_position_z"): z,
    }

    for i, name in enumerate(real_names):
        field_name = f"particle_{name}"
        pt_data[(ptype, field_name)] = reals[:, i]

    #ds = load_particles(pt_data, bbox=bbox, n_dim=3, length_unit="cm")
    ds = load_particles(pt_data, bbox=bbox, length_unit="cm")
    print("\n=== yt dataset created ===")
    print("Dataset:", ds)
    print("Current time:", ds.current_time)
    print("Domain left edge:", ds.domain_left_edge)
    print("Domain right edge:", ds.domain_right_edge)

    # --------------------------------------------------------------
    # 4. Simple data inspection
    # --------------------------------------------------------------
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

    print("\nFirst 5 values of each real component:")
    for name in real_names:
        field_name = f"particle_{name}"
        arr = ad[ptype, field_name]
        print(f"  {field_name}: ", [f"{arr[i].v:.3e}" for i in range(min(5, npart_ds))])

    # --------------------------------------------------------------
    # 5. Optional: scatter plot of x–y positions
    # --------------------------------------------------------------
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

