# part.md — Main Code and Particle Structure

This document gives a short, practical overview of:

- how the main driver code is organized, and  
- how the particle data structure is defined and used.

It is written to match the current STOICREX / NeighborList example layout.

---

## 1. High–level overview

The code is a small molecular–dynamics style test built on top of AMReX’s particle infrastructure. The key ideas are:

- Use AMReX to define a 3D periodic box and decompose it into grids and tiles.
- Represent particles with AMReX’s `ParticleContainer` and `NeighborParticleContainer`.
- Build a neighbor list using a geometric cutoff.
- Loop over neighbors to compute forces, update particle accelerations and velocities, and move particles.
- Optionally write out plotfiles (AMReX format) and VTK point clouds for visualization.

The main objects involved are:

- `main.cpp`  
  Sets up AMReX, reads parameters, constructs geometry, creates the particle container, runs the time loop, and calls I/O helpers.

- `MDParticleContainer.[H,cpp]`  
  A custom particle container derived from AMReX classes that stores velocities and accelerations and implements initialization, force computation, and time integration.

- `FieldIO.[H,cpp]`  
  Routines to write AMReX plotfiles and a simple VTK file with particle positions and properties.

- `CheckPair.H`  
  A tiny helper that decides whether two particles are close enough to be considered neighbors.

- `Constants.H`  
  Global constants (cutoff radius, minimum allowed separation, etc.).

---

## 2. File–level structure

A quick map of the most relevant source files:

- `main.cpp`  
  - Defines a `TestParams` struct with domain size, maximum grid size, runtime options, etc.  
  - Uses `amrex::ParmParse` to read parameters from the input file (for example, under a `test` or similar namespace).  
  - Creates the AMReX geometry, box array, distribution mapping, and a `MDParticleContainer` instance.  
  - Initializes particles and runs the main time integration loop.  
  - Prints diagnostic quantities such as minimum distance or total number of particles.  
  - Calls I/O helpers at the end of the run (and/or at regular intervals).

- `MDParticleContainer.H`  
  - Declares:
    - the `PIdx` enumeration (mapping real component indices to names),
    - the `MDParticleContainer` class and its public interface.

- `MDParticleContainer.cpp`  
  - Implements:
    - particle initialization (`InitParticles`),
    - neighbor list support,
    - force computation (`computeForces`),
    - time step selection (`computeStepSize`),
    - particle movement (`moveParticles`),
    - writing particles (`writeParticles`).

- `FieldIO.H` and `FieldIO.cpp`  
  - Provide:
    - `WritePlotFile(const MDParticleContainer& pc, const amrex::Vector<amrex::Geometry>& geom, int nstep)`  
      to write an AMReX-style plotfile, plus embedded particle checkpoint.
    - `WriteParticlesVTK(const MDParticleContainer& pc, int nstep)`  
      to write all particles into a simple legacy VTK file for ParaView or VisIt.

- `CheckPair.H`  
  - Provides a small device–callable functor that tests whether a pair of particles is within a search radius based on the global cutoff.

- `Constants.H`  
  - Contains constants in the `Params` namespace, most notably
    - `cutoff` – physical interaction cutoff radius, and  
    - `min_r` – minimum allowed separation (to avoid singularities).

---

## 3. Particle structure

### 3.1 Real component indices (PIdx)

Particle extra data (beyond position and builtin ID/CPU) is accessed by index via `rdata(k)`. The mapping from indices to physical meaning is centralized in `PIdx`:

```cpp
struct PIdx
{
    enum {
        vx = 0,
        vy, vz,  // velocity components
        ax, ay, az,  // acceleration (or force per mass) components
        ncomps
    };
};
```

So for a given particle `p` of type `MDParticleContainer::ParticleType`:

- Position:
  - `p.pos(0)`  -> x  
  - `p.pos(1)`  -> y  
  - `p.pos(2)`  -> z  

- Velocity:
  - `p.rdata(PIdx::vx)` -> vx  
  - `p.rdata(PIdx::vy)` -> vy  
  - `p.rdata(PIdx::vz)` -> vz  

- Acceleration:
  - `p.rdata(PIdx::ax)` -> ax  
  - `p.rdata(PIdx::ay)` -> ay  
  - `p.rdata(PIdx::az)` -> az  

`PIdx::ncomps` is the total number of real components stored with each particle.

### 3.2 MDParticleContainer class (conceptual)

`MDParticleContainer` is built on AMReX’s neighbor–aware container. At a high level, the class:

- Stores particle positions and their associated real components.
- Manages the AMReX neighbor list.
- Provides:

  - `InitParticles(...)`
  - `computeForces()`
  - `minDistance()`
  - `computeStepSize(cfl)`
  - `moveParticles(dt)`
  - `writeParticles(n)`

---

## 4. Pair search and cutoff (CheckPair)

`CheckPair` filters candidate pairs using a geometric criterion:

```cpp
bool operator()(const P& p1, const P& p2) const
{
    Real dx = p1.pos(0) - p2.pos(0);
    Real dy = p1.pos(1) - p2.pos(1);
    Real dz = p1.pos(2) - p2.pos(2);
    Real dsq = dx*dx + dy*dy + dz*dz;
    return (dsq <= 25.0 * Params::cutoff * Params::cutoff);
}
```

- `cutoff` is the physical interaction radius.
- The neighbor list radius is `5 * cutoff` to reduce rebuild frequency.

---

## 5. Main driver structure (`main.cpp`)

The simulation loop generally looks like:

1. **Initialize AMReX**
2. **Read inputs (ParmParse → TestParams)**
3. **Build geometry**
4. **Create MDParticleContainer**
5. **Initialize particles**
6. **Time loop**  
   - rebuild neighbor list  
   - compute forces  
   - compute or update `dt`  
   - move particles  
   - diagnostics  
   - optional plotfile / VTK output
7. **Finalize**

---

## 6. Output formats and particle fields

### 6.1 AMReX Plotfiles

A directory `pltXXXXX/` contains:

- a top-level AMReX grid `Header`,  
- a `Level_0/` folder (grid data),  
- a `particle0/` folder containing:
  - `Header` (names + counts)
  - `DATA_00000` (binary per-particle data)
  - `Particle_H` (grid bounds for bins)

Particle fields written:

- `vx, vy, vz` (velocity)
- `ax, ay, az` (acceleration)

### 6.2 VTK particle dumps

`WriteParticlesVTK()` writes ASCII:

- `particles_00000.vtk`
- `particles_00010.vtk`

Each contains:

- `POINTS` (x,y,z)
- `POINT_DATA` arrays for:
  - vx, vy, vz
  - ax, ay, az

---

## 7. Extending the particle structure

To add a new particle field:

1. Add an enum entry in `PIdx`.  
2. Update initializers.  
3. Add variable name to I/O in `FieldIO.cpp`.  
4. Optionally add to VTK output.

This keeps particle layout centralized and easy to modify.

---
