# Quickstart Guide

This document explains how to **download**, **install**, **compile**, and **run** the STOICREX molecular-dynamics (MD) / AMReX-based code.

---

## 1. Requirements

### Operating System
- macOS (Intel or Apple Silicon)
- Linux (Ubuntu, Debian, Arch, CentOS, etc.)

### Dependencies
The code uses:
- **AMReX**
- **C++17 compiler**
- **GNU Make**
- **MPI (optional)**
- **Python** (for analysis scripts)

Supported compilers:
- `g++` (>= 10)
- `clang++` (>= 12)
- `icpx` (Intel oneAPI)
- `mpic++` for MPI mode (optional)

---

## 2. Download the Repository

```bash
git clone https://github.com/<YOUR_ORG>/stoicrex.git
cd stoicrex
```

## 3.Install Dependencies (AMReX)

A convenience installer is provided under lib
```bash
./install.sh amrex
```
This script will:
Download AMReX (v 25.11)


## 4. Build the code


At present the code is in `exec/NeighborList`

TO BE CHANGE

compile
```bash
make -j4
```

to use MPI, edit in `GNUmakefile`

```
USE_MPI   = FALSE
```

## 5. Run the code

```bash
./main3d.gnu.ex inputs
```

Parallel run (with 4 cores)

```bash
mpirun -np 4 ./main3d.gnu.MPI.ex inputs
```

## 6. Output

You will files like :

```bash
particles_00000.vtk
particles_00010.vtk
```

These can be opened directly in ParaView or VisIt.